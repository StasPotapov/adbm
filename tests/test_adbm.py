"""Unit tests for the adbm CLI: no device needed. Run: python3 -m unittest discover tests"""
import contextlib
import importlib.machinery
import io
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
TMP = tempfile.mkdtemp(prefix="adbm-test-")
os.environ["ADBM_CACHE"] = os.path.join(TMP, "cache")
os.environ["ADBM_PROJECT"] = os.path.join(TMP, "project")
os.makedirs(os.environ["ADBM_PROJECT"], exist_ok=True)


def load_cli():
    loader = importlib.machinery.SourceFileLoader("adbm_cli", os.path.join(ROOT, "skill", "bin", "adbm"))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("adbm_cli", loader))
    loader.exec_module(mod)
    return mod


adbm = load_cli()


def setUpModule():
    # the CLI reads small files with open().read(): not a leak in a short-lived process
    warnings.simplefilter("ignore", ResourceWarning)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)

try:
    from PIL import Image
except ImportError:
    Image = None


def png(path, size=(100, 200), color=(250, 250, 250), boxes=()):
    """A synthetic frame: a solid colour with filled boxes [(x0, y0, x1, y1, colour)]."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.new("RGB", size, color)
    for x0, y0, x1, y1, c in boxes:
        im.paste(c, (x0, y0, x1, y1))
    im.save(path)
    return path


class TreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = adbm.parse_nodes(open(os.path.join(FIX, "settings-api33.xml")).read())

    def test_parse_skips_empty_and_system_ui(self):
        self.assertTrue(self.nodes)
        self.assertTrue(all(n["text"] or n["desc"] or n["id"] or n["flags"] for n in self.nodes))
        self.assertEqual([n["i"] for n in self.nodes], list(range(len(self.nodes))))

    def test_find_exact_then_substring(self):
        hit = adbm.find_nodes(self.nodes, "Батарея")
        self.assertEqual(hit[0]["text"], "Батарея")
        self.assertTrue(adbm.find_nodes(self.nodes, "settings_homepage_container"))
        self.assertTrue(adbm.find_nodes(self.nodes, "батар"))
        self.assertFalse(adbm.find_nodes(self.nodes, "нет такого"))

    def test_fmt_full_and_compact(self):
        nd = adbm.find_nodes(self.nodes, "Батарея")[0]
        self.assertRegex(adbm.fmt_node(nd), r'^\[\d+\] TextView "Батарея".* @\d+,\d+')
        compact = adbm.fmt_node(nd, False)
        self.assertNotIn("@", compact)
        self.assertNotIn("TextView", compact)

    def test_tree_text_feeds_ui_diff(self):
        p = os.path.join(TMP, "frame.ui.txt")
        open(p, "w").write(adbm.tree_text(self.nodes, limit=None))
        m = adbm.ui_lines_to_map(p)
        self.assertIn("Батарея", m)

    def test_screen_change(self):
        after = [n for n in self.nodes if n["text"] != "Батарея"]
        self.assertEqual(adbm.screen_change(self.nodes, self.nodes), "screen unchanged")
        self.assertIn('-1 "Батарея"', adbm.screen_change(self.nodes, after))
        sw = {"text": "", "desc": "", "id": "switch_widget", "near": "Wi-Fi", "flags": ["click", "check"]}
        bt = dict(sw, near="Bluetooth", flags=["click", "check", "on"])
        self.assertEqual(adbm.screen_change([sw, bt], [dict(sw, flags=["click", "check", "on"]), bt]), '"Wi-Fi" on')
        on_text = dict(sw, text="ON", flags=["check", "on"])
        self.assertEqual(adbm.screen_change([on_text], [dict(on_text, text="OFF", flags=["check"])]), '"Wi-Fi" off')

    def test_unlabeled_switch_gets_its_row(self):
        xml = ('<?xml version="1.0"?><hierarchy><node text="Wi-Fi" bounds="[0,100][800,200]" />'
               '<node text="" resource-id="android:id/switch_widget" checkable="true" checked="false" '
               'clickable="true" bounds="[900,110][1000,190]" /></hierarchy>')
        sw = [n for n in adbm.parse_nodes(xml) if "check" in n["flags"]][0]
        self.assertEqual(adbm.node_label(sw), "Wi-Fi")

    def test_match_kind(self):
        nd = adbm.find_nodes(self.nodes, "Батарея")[0]
        self.assertEqual(adbm.match_kind(nd, "Батарея"), ("text", "Батарея"))
        self.assertEqual(adbm.match_kind(nd, "атаре"), ("text", ".*атаре.*"))
        idn = adbm.find_nodes(self.nodes, "settings_homepage_container")[0]
        self.assertEqual(adbm.match_kind(idn, "settings_homepage_container")[0], "id")


class ParseTest(unittest.TestCase):
    def test_matrix(self):
        cells, keys = adbm.parse_matrix(["nav=threebutton,gestural", "theme=light,dark font=1.0"])
        self.assertEqual(keys, ["nav", "theme", "font_scale"])
        self.assertEqual(len(cells), 4)
        self.assertIn({"nav": "gestural", "theme": "dark", "font_scale": "1.0"}, cells)
        with self.assertRaises(SystemExit):
            adbm.parse_matrix(["color=red"])

    def test_crop(self):
        self.assertEqual(adbm.parse_crop("-5,10,2000,20", 1080, 2400), (0, 10, 1080, 20))
        for bad in ("1,2,3", "50,50,10,10", "a,b,c,d"):
            with self.assertRaises(SystemExit):
                adbm.parse_crop(bad, 1080, 2400)

    def test_flow_timeouts_follow_run_flow(self):
        d = tempfile.mkdtemp(dir=TMP)
        open(os.path.join(d, "sub.yaml"), "w").write("appId: x\n---\n- extendedWaitUntil:\n    timeout: 30000\n")
        open(os.path.join(d, "main.yaml"), "w").write("appId: x\n---\n- runFlow: sub.yaml\n- assertVisible:\n    timeout: 5000\n")
        self.assertEqual(sorted(adbm.flow_timeouts(os.path.join(d, "main.yaml"))), [5000, 30000])

    def test_state_hint(self):
        self.assertIn("USB debugging", adbm.state_hint("unauthorized"))
        self.assertIn("udev", adbm.state_hint("no permissions (user u is not in the plugdev group); see [http://x]"))

    def test_read_verdicts(self):
        run = tempfile.mkdtemp(dir=TMP)
        notes = open(os.path.join(FIX, "notes.md")).read()
        open(os.path.join(run, "notes.md"), "w").write("## adbm-eyes verdict\n\n- PROBLEM api33/old — x\n\n" + notes)
        worst, per_api, summary, _ = adbm.read_verdicts(run)
        self.assertTrue(summary.startswith("При system=dark"))
        self.assertEqual(worst[("light", "1-empty-list")], "problem")
        self.assertEqual(worst[("dark", "2-settings")], "expected")
        self.assertEqual(per_api[("light", "2-settings", 35)][0], "problem")
        self.assertNotIn(("", "old"), worst)


class FrameTest(unittest.TestCase):
    def test_frame_problem(self):
        empty = os.path.join(TMP, "empty.png")
        open(empty, "wb").close()
        self.assertEqual(adbm.frame_problem(empty), "broken")
        if Image is None:
            self.skipTest("no Pillow")
        black = png(os.path.join(TMP, "black.png"), color=(0, 0, 0), boxes=[(0, 0, 100, 10, (200, 200, 200))])
        self.assertEqual(adbm.frame_problem(black), "black")
        text = png(os.path.join(TMP, "dark.png"), color=(10, 10, 10), boxes=[(20, 80, 60, 90, (255, 255, 255))])
        self.assertIsNone(adbm.frame_problem(text))

    def test_scan_run_both_layouts(self):
        if Image is None:
            self.skipTest("no Pillow")
        run = tempfile.mkdtemp(dir=TMP)
        png(os.path.join(run, "api35", "after", "dark", "1-a.png"))
        png(os.path.join(run, "api35", "before", "dark", "1-a.png"))
        png(os.path.join(run, "api33", "old", "2-b-after.png"))
        frames = adbm.scan_run(run)
        self.assertEqual(set(frames[("dark", "1-a")][35]), {"before", "after"})
        self.assertIn("after", frames[("old", "2-b")][33])


@unittest.skipIf(Image is None, "no Pillow")
class DiffTest(unittest.TestCase):
    SIZE = (400, 800)  # status bar = top 4% = 32 px

    def pair(self, before_boxes=(), after_boxes=()):
        d = tempfile.mkdtemp(dir=TMP)
        b = png(os.path.join(d, "b.png"), self.SIZE, boxes=before_boxes)
        a = png(os.path.join(d, "a.png"), self.SIZE, boxes=after_boxes)
        return b, a, os.path.join(d, "diff", "x.png")

    def test_identical(self):
        b, a, out = self.pair()
        r = adbm.diff_pair(b, a, out, 0.04)
        self.assertTrue(r["same"])
        self.assertEqual(r["files"], {})

    def test_small_change_gives_diff_and_crop(self):
        b, a, out = self.pair(after_boxes=[(100, 400, 200, 440, (20, 20, 200))])
        r = adbm.diff_pair(b, a, out, 0.04)
        self.assertFalse(r["same"])
        self.assertEqual(r["bbox"], [100, 400, 200, 440])
        self.assertEqual(set(r["files"]), {"diff", "crop"})
        with Image.open(r["files"]["diff"]) as im:
            self.assertLessEqual(im.width, adbm.DIFF_W)

    def test_status_bar_icons_count_clock_does_not(self):
        b, a, out = self.pair(after_boxes=[(10, 5, 60, 25, (0, 0, 0))])  # the clock area, left
        self.assertTrue(adbm.diff_pair(b, a, out, 0.04)["same"])
        b, a, out = self.pair(after_boxes=[(300, 5, 390, 25, (0, 0, 0))])  # icons, right
        r = adbm.diff_pair(b, a, out, 0.04)
        self.assertFalse(r["same"])
        self.assertTrue(r["status_bar"] and r["content_same"])
        self.assertIn("top", r["files"])

    def test_same_change(self):
        r1 = {"same": False, "status_bar": False, "ui": [], "note": "", "pct": 2.5, "bbox": [45, 483, 1035, 582]}
        r2 = dict(r1, pct=2.6, bbox=[45, 552, 1035, 651])
        self.assertTrue(adbm.same_change(r1, r2))
        self.assertFalse(adbm.same_change(r1, dict(r2, pct=4.0)))
        self.assertFalse(adbm.same_change(r1, dict(r2, status_bar=True)))


class SaveFlowTest(unittest.TestCase):
    def test_journal_to_flow(self):
        cache = os.environ["ADBM_CACHE"]
        os.makedirs(cache, exist_ok=True)
        root = adbm.project_root()
        ents = [
            {"op": "launch", "package": "com.example", "clear": True},
            {"op": "tap", "by": "text", "sel": "Sign in", "text": "Sign in", "desc": "", "id": "", "scrolled": 2},
            {"op": "wait", "by": "id", "value": "email", "timeout": 8},
            {"op": "type", "text": "Привет"},
            {"op": "clear_field", "n": 7},
            {"op": "tap", "text": "Photo", "desc": "", "id": "", "how": "double"},
            {"op": "swipe", "direction": "10,20,30,40", "points": [108, 480, 324, 960], "screen": [1080, 2400]},
            {"op": "assert", "by": "text", "value": "Done", "timeout": 0},
            {"op": "shot", "name": "1-done", "group": ""},
        ]
        with open(os.path.join(cache, "session.jsonl"), "w") as f:
            for e in ents:
                f.write(json.dumps({"t": 0, "project": root, "api": 35, **e}, ensure_ascii=False) + "\n")
        out = os.path.join(TMP, "flow.yaml")
        args = type("A", (), {"api": "35", "app": None, "out": out, "force": True, "slug": "x"})()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(adbm.cmd_save_flow(args), 0)
        flow = open(out).read()
        for part in ("appId: com.example", "clearState: true", "scrollUntilVisible", 'tapOn: "Sign\\\\ in"',
                     "extendedWaitUntil", 'id: "email"', "timeout: 8000", 'inputText: "Привет"', "eraseText: 7",
                     "doubleTapOn", 'start: "10%,20%"', "assertVisible", 'takeScreenshot: "1-done"'):
            self.assertIn(part, flow)


class ToolsTest(unittest.TestCase):
    def test_guard_hook(self):
        hook = os.path.join(ROOT, "skill", "hooks", "adbm-guard.py")

        def decide(path):
            r = subprocess.run([sys.executable, hook], input=json.dumps({"tool_input": {"file_path": path}}),
                               capture_output=True, text=True)
            return "deny" if "deny" in r.stdout else "allow"
        self.assertEqual(decide("/p/build/adbm/r/api35/after/dark/1.png"), "deny")
        self.assertEqual(decide("/p/build/adbm/r/logs/ui-api35-last.xml"), "deny")
        self.assertEqual(decide("/p/build/adbm/r/diff/api35/dark/1.crop.png"), "allow")
        self.assertEqual(decide("/p/build/adbm/r/00-summary.png"), "allow")
        self.assertEqual(decide("/p/src/api35/icon.png"), "allow")

    def test_install_guard_keeps_settings(self):
        cfg = tempfile.mkdtemp(dir=TMP)
        base = {"model": "x", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "a"}]}]}}
        with open(os.path.join(cfg, "settings.json"), "w") as f:
            json.dump(base, f)
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        try:
            adbm.install_guard()
            adbm.install_guard()
            with open(os.path.join(cfg, "settings.json")) as f:
                got = json.load(f)
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]
        self.assertEqual(got["model"], "x")
        self.assertEqual(got["hooks"]["PreToolUse"][0], base["hooks"]["PreToolUse"][0])
        self.assertEqual(len(got["hooks"]["PreToolUse"]), 2)
        self.assertTrue(adbm.guard_installed(got))

    def test_install_through_symlink_and_agent_backup(self):
        cfg = tempfile.mkdtemp(dir=TMP)
        real = os.path.join(TMP, "dotfiles-settings.json")
        with open(real, "w") as f:
            json.dump({"hooks": None}, f)
        os.chmod(real, 0o600)
        os.symlink(real, os.path.join(cfg, "settings.json"))
        os.makedirs(os.path.join(cfg, "agents"))
        with open(os.path.join(cfg, "agents", "adbm-eyes.md"), "w") as f:
            f.write("my edits")
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        try:
            adbm.install_guard()
            adbm.install_agent()
            link = adbm.agent_link()
            self.assertTrue(os.path.islink(os.path.join(cfg, "settings.json")))
            with open(real) as f:
                self.assertTrue(adbm.guard_installed(json.load(f)))
            self.assertEqual(os.stat(real).st_mode & 0o777, 0o600)
            self.assertEqual(os.path.realpath(link), adbm.agent_target())
            with open(link + ".adbm-backup") as f:
                self.assertEqual(f.read(), "my edits")
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]

    def test_config_project_over_user(self):
        xdg = os.path.join(TMP, "xdg")
        os.makedirs(os.path.join(xdg, "adbm"), exist_ok=True)
        os.makedirs(os.path.join(os.environ["ADBM_PROJECT"], ".adbm"), exist_ok=True)
        user = os.path.join(xdg, "adbm", "config.ini")
        proj = os.path.join(os.environ["ADBM_PROJECT"], ".adbm", "config.ini")
        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = xdg
        try:
            cfg, problems = adbm.load_config()
            self.assertEqual(cfg["adbm-eyes"], {"model": ("haiku", "default"), "effort": ("low", "default")})
            open(user, "w").write(adbm.CONFIG_TEMPLATE.replace("model = haiku", "model = sonnet   # sharper"))
            open(proj, "w").write("[adbm-eyes]\neffort = medium\n")
            cfg, problems = adbm.load_config()
            self.assertEqual(problems, [])
            self.assertEqual(cfg["adbm-eyes"], {"model": ("sonnet", "user"), "effort": ("medium", "project")})
            open(proj, "w").write("[DEFAULT]\nmodel = opus\n[adbm-eyes]\neffort = High\n")
            cfg, problems = adbm.load_config()
            self.assertEqual(cfg["adbm-eyes"], {"model": ("sonnet", "user"), "effort": ("high", "project")})
            self.assertEqual(len(problems), 1)
            open(proj, "w").write("[adbm-eyes]\neffort = turbo\nmodel = claude-x\nmodl = x\n[eyes]\n")
            cfg, problems = adbm.load_config()
            self.assertEqual(cfg["adbm-eyes"], {"model": ("sonnet", "user"), "effort": ("low", "user")})
            self.assertEqual(len(problems), 4)
        finally:
            if old is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = old
            if os.path.exists(proj):
                os.remove(proj)

    def test_guard_command_quotes_the_path(self):
        cmd = adbm.guard_command()
        self.assertRegex(cmd, r'^f=("\$HOME/[^"]+"|\S+); \[ -f "\$f" \]')

    def test_measure_session(self):
        tr = os.path.join(TMP, "t.jsonl")
        with open(tr, "w") as f:
            f.write(json.dumps({"message": {"content": [{"type": "tool_use", "id": "1", "name": "Bash",
                                                         "input": {"command": '"$ADBM" ui --api 35'}}]}}) + "\n")
            f.write(json.dumps({"message": {"content": [{"type": "tool_result", "tool_use_id": "1",
                                                         "content": "x" * 400}]}}) + "\n")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "measure-session.py"), tr],
                           capture_output=True, text=True)
        self.assertRegex(r.stdout, r"adbm ui\s+1\s+400\s+100")


if __name__ == "__main__":
    unittest.main()
