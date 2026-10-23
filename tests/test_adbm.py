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
import types
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


class BatchTest(unittest.TestCase):
    def steps(self, *steps):
        err = io.StringIO()
        with contextlib.redirect_stdout(err), contextlib.redirect_stderr(err):
            try:
                return adbm.batch_steps(steps, adbm.build_parser())
            except SystemExit:
                return err.getvalue()

    def test_parse(self):
        res = self.steps("tap 'Sign in' --expect Done", "type a@b.c", "key back --ap 33")
        self.assertEqual([ns.fn for _, ns in res], [adbm.cmd_tap, adbm.cmd_type, adbm.cmd_key])
        self.assertEqual(res[0][1].selector, "Sign in")
        self.assertEqual((res[0][1].api, res[0][1].serial), (None, None))
        # an abbreviated flag still names the step's own device
        self.assertEqual(res[2][1].api, "33")

    def test_rejected_before_any_step(self):
        self.assertIn("step [2]", self.steps("tap OK", "batch 'tap OK'"))
        self.assertIn("step [1]", self.steps("shot x"))
        self.assertIn("step [2]", self.steps("tap OK", "tap --no-such-flag OK"))
        self.assertIn("step [1]", self.steps("type 'unclosed"))
        out = self.steps("tap -h")
        self.assertIn("help is not a step", out)
        self.assertNotIn("usage:", out)

    def run_batch(self, steps, keep_going=False, **dev):
        out = io.StringIO()
        a = types.SimpleNamespace(steps=steps, ui=False, keep_going=keep_going, api=None, serial=None, **dev)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = adbm.cmd_batch(a)
        return rc, out.getvalue().splitlines()[-1]

    def test_stop_keep_going_and_devices(self):
        calls = []

        def ok(a):
            calls.append((a.text, adbm.pick(a)[0][1]))
            return 0

        def bad(a):
            calls.append((a.text, adbm.pick(a)[0][1]))
            adbm.die("not found")

        def boom(a):
            raise ValueError("broken XML")
        table = {"a": ok, "b": bad, "c": ok, "d": boom}
        picks = []

        def fake_pick(args, multi=False):
            if getattr(args, "picked", None):
                return [args.picked]
            picks.append(args.serial)
            return [(35, args.serial or "emulator-5556")]

        def fake_steps(steps, parser):
            return [(t.split()[0], types.SimpleNamespace(fn=table[t.split()[0]], text=t.split()[0], cmd="tap",
                                                          api=None, serial=t.split()[1] if " " in t else None))
                    for t in steps]
        saved = adbm.pick, adbm.batch_steps
        adbm.pick, adbm.batch_steps = fake_pick, fake_steps
        try:
            self.assertEqual(self.run_batch(["a", "b", "c"]), (1, "batch: 1 of 3 ok, stopped at [2]"))
            self.assertEqual(calls, [("a", "emulator-5556"), ("b", "emulator-5556")])
            self.assertEqual(picks, [None])  # one device lookup for the whole batch
            calls.clear()
            self.assertEqual(self.run_batch(["a", "d", "b", "c"], keep_going=True),
                             (1, "batch: 2 of 4 ok, failed [2], [3]"))
            self.assertEqual([t for t, _ in calls], ["a", "b", "c"])
            # every step names its device: no batch device needed
            calls.clear()
            picks.clear()
            self.assertEqual(self.run_batch(["a emulator-5558"]), (0, "batch: 1 of 1 ok"))
            self.assertEqual(calls, [("a", "emulator-5558")])
            self.assertEqual(picks, ["emulator-5558"])
        finally:
            adbm.pick, adbm.batch_steps = saved


class CrashesTest(unittest.TestCase):
    def fix(self, name):
        return open(os.path.join(FIX, name)).read()

    def test_logcat(self):
        lc = adbm.parse_logcat_crashes(self.fix("crash-logcat-api35.txt"))
        self.assertEqual([(c["kind"], c["process"], c["pid"]) for c in lc],
                         [("native", "com.google.android.tts", 2426), ("java", "com.android.settings", 5355)])
        self.assertTrue(lc[0]["title"].startswith("signal 4 (SIGILL)"))
        self.assertIn("shell-induced crash", lc[1]["title"])

    def test_merge_with_dropbox(self):
        lc = adbm.parse_logcat_crashes(self.fix("crash-logcat-api35.txt"))
        db = adbm.parse_dropbox(self.fix("crash-dropbox-api35.txt"))
        self.assertEqual(len(db), 2)
        res = adbm.merge_crashes(lc, db)
        self.assertEqual([c["id"] for c in res], ["1023-132829-5355", "1023-132656-2426"])
        self.assertEqual([c["sources"] for c in res], [["logcat", "dropbox"]] * 2)
        # after a reboot only dropbox has them: the ids do not change
        self.assertEqual([c["id"] for c in adbm.merge_crashes([], adbm.parse_dropbox(self.fix("crash-dropbox-api35.txt")))],
                         ["1023-132829-5355", "1023-132656-2426"])

    def test_lost_dropbox_entries_join_logcat(self):
        res = adbm.merge_crashes(adbm.parse_logcat_crashes(self.fix("crash-logcat-api33.txt")),
                                 adbm.parse_dropbox(self.fix("crash-dropbox-api33.txt")))
        self.assertEqual([(c["process"], c["pid"]) for c in res],
                         [("com.android.settings", 7188), ("com.android.settings", 4953)])

    def test_anr(self):
        text = ("========================================\n2026-10-23 14:00:01 data_app_anr (text, 900 bytes)\n"
                "Process: com.example\nPID: 777\nSubject: Input dispatching timed out\n\n----- pid 777 -----\n")
        c = adbm.merge_crashes([], adbm.parse_dropbox(text))[0]
        self.assertEqual((c["kind"], c["process"], c["pid"], c["title"], c["id"]),
                         ("anr", "com.example", 777, "Input dispatching timed out", "1023-140001-777"))

    def test_tombstone_copy_and_anr_stay_apart(self):
        db = self.fix("crash-dropbox-api35.txt")
        native = db[db.index("========================================\n2026-10-23 13:26:56 system_app_native_crash"):]
        tomb = native.replace("13:26:56 system_app_native_crash", "13:26:57 SYSTEM_TOMBSTONE", 1)
        anr = ("========================================\n2026-10-23 13:28:30 system_app_anr (text, 90 bytes)\n"
               "Process: com.android.settings\nPID: 5355\nSubject: Broadcast of Intent\n\nProcess: other\nPID: 1\n")
        res = adbm.merge_crashes(adbm.parse_logcat_crashes(self.fix("crash-logcat-api35.txt")),
                                 adbm.parse_dropbox(db + tomb + anr))
        self.assertEqual([(c["kind"], c["pid"]) for c in res], [("anr", 5355), ("java", 5355), ("native", 2426)])
        self.assertEqual(res[0]["title"], "Broadcast of Intent")
        self.assertIn("shell-induced crash", res[1]["title"])
        self.assertEqual(res[0]["id"], "1023-132830-5355")

    def test_parse_when(self):
        now = adbm.dt.datetime(2026, 1, 5, 12, 0)
        D = adbm.dt.datetime
        self.assertEqual(adbm.parse_when("6h", now), (D(2026, 1, 5, 6, 0), True))
        self.assertEqual(adbm.parse_when("90min", now), (D(2026, 1, 5, 10, 30), True))
        self.assertEqual(adbm.parse_when("2026-01-04 18:30", now), (D(2026, 1, 4, 18, 30), True))
        self.assertEqual(adbm.parse_when("01-04", now), (D(2026, 1, 4), False))
        self.assertEqual(adbm.parse_when("1-4", now), (D(2026, 1, 4), False))
        # later today stays this year; a day that has not come yet is last year's
        self.assertEqual(adbm.parse_when("01-05 18:00", now)[0], D(2026, 1, 5, 18, 0))
        self.assertEqual(adbm.parse_when("12-31 23:00", now)[0], D(2025, 12, 31, 23, 0))
        # 02-29 only in a leap year
        self.assertEqual(adbm.parse_when("02-29", adbm.dt.datetime(2029, 3, 1))[0], D(2028, 2, 29))
        with contextlib.redirect_stderr(io.StringIO()):
            for bad in ("yesterday", "3m", "13-40"):
                with self.assertRaises(SystemExit):
                    adbm.parse_when(bad, now)

    def test_registers_hidden(self):
        self.assertTrue(adbm.REGISTERS.match("    rax 0000000000000000  rbx 00007ffd1c2e3f40  rcx 0000000000000000"))
        self.assertTrue(adbm.REGISTERS.match("    cs  0000000000000033  ss  000000000000002b"))
        self.assertTrue(adbm.REGISTERS.match("    x0  000000741458e278  x1  000000741458e24c  x2  000000741458e24c"))
        self.assertTrue(adbm.REGISTERS.match("    lr  0000007413adc1e8  sp  0000007367f30500  pc  0000007413b09b74  pst 0000000080000000"))
        self.assertFalse(adbm.REGISTERS.match("      #00 pc 0000000001b72b74  /data/app/lib.so"))


class MobilecliTest(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(adbm, k) for k in ("sh", "adb", "ashell", "adb_ok", "mobilecli_bin", "screen_size")}
        self.calls = []
        adbm.mobilecli_bin = lambda: "/bin/mobilecli"
        adbm.ashell = lambda s, cmd, timeout=60: self.calls.append(("shell", s, cmd)) or (
            ("isVisible=true" if self.visible else "isVisible=false") if cmd.startswith("dumpsys") else self.xml)
        adbm.MOBILECLI_IDS.clear()
        self.visible = True
        adbm.adb_ok = lambda s, cmd, timeout=60: self.calls.append(("ok", s, cmd)) or (True, "")
        adbm.adb = lambda s, *args, timeout=60, binary=False: (0, "Pixel_8_API_35\nOK", "")
        adbm.screen_size = lambda s: (1080, 2400)
        self.xml = ""

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(adbm, k, v)

    def fake_sh(self, ids, answer):
        def sh(cmd, timeout=120, **kw):
            self.calls.append(("sh", cmd))
            if cmd[1] == "devices":
                return 0, json.dumps({"status": "ok", "data": {"devices": [{"id": i} for i in ids]}}), ""
            return 0, json.dumps(answer), ""
        adbm.sh = sh

    def test_avd_name_and_agent_stopped(self):
        self.fake_sh(["emulator-5554", "Pixel_8_API_35"], {"status": "ok", "data": {"text": "Привет"}})
        self.assertEqual(adbm.mobilecli("emulator-5556", "io", "clipboard", "get"), (True, {"text": "Привет"}))
        self.assertIn(("sh", ["/bin/mobilecli", "io", "clipboard", "get", "--device", "Pixel_8_API_35"]), self.calls)
        self.assertTrue(self.calls[-1][2].startswith("pkill -f 'com.mobilenext.mobilecli.DeviceServe[r]';"))
        # a text that looks like a flag goes after --; the id is looked up once
        self.calls.clear()
        adbm.mobilecli("emulator-5556", "io", "clipboard", "set", text="-5 ₽")
        self.assertEqual([c[1] for c in self.calls if c[0] == "sh"],
                         [["/bin/mobilecli", "io", "clipboard", "set", "--device", "Pixel_8_API_35", "--", "-5 ₽"]])

    def test_unknown_device_and_error(self):
        self.fake_sh(["emulator-5554"], {"status": "error", "error": "boom"})
        self.assertEqual(adbm.mobilecli("R5CT", "io", "clipboard", "get"), (False, "mobilecli does not see R5CT"))
        self.assertFalse(any(c[0] == "shell" for c in self.calls))  # nothing ran on the device: nothing to stop
        self.assertEqual(adbm.mobilecli("emulator-5554", "io", "clipboard", "get"), (False, "boom"))

    def test_type_checks_the_field(self):
        self.fake_sh(["e"], {"status": "ok", "data": {}})
        field = '<hierarchy><node text="{}" resource-id="q" class="android.widget.EditText" focused="true" {} bounds="[0,0][100,50]" /></hierarchy>'
        self.xml = field.format("Привет мир", 'password="false"')
        self.assertEqual(adbm.type_clipboard("e", 28, "Привет мир"), (True, "", False))
        self.xml = field.format("", 'password="false"')
        ok, msg, fallback = adbm.type_clipboard("e", 28, "Привет мир")
        self.assertEqual((ok, fallback), (False, False))
        self.assertIn("may not accept paste", msg)
        self.xml = field.format("••••", 'password="true"')
        self.assertTrue(adbm.type_clipboard("e", 28, "пароль")[0])
        self.xml = "<hierarchy></hierarchy>"
        self.assertIn("no focused field", adbm.type_clipboard("e", 28, "x")[1])
        # mobilecli failed before the paste: Maestro may type instead
        adbm.MOBILECLI_IDS.clear()
        self.fake_sh([], {})
        self.assertEqual(adbm.type_clipboard("e", 28, "x"), (False, "mobilecli: mobilecli does not see e", True))

    def test_overlay_dismiss(self):
        btn = '<node resource-id="com.android.systemui:id/dismiss_button" class="x" bounds="[126,1333][252,1459]" />'
        prev = '<node resource-id="com.android.systemui:id/clipboard_preview" class="x" bounds="[53,1259][263,1469]" />'
        self.xml = prev + btn
        adbm.clip_overlay_dismiss("e", 35)
        self.assertEqual(self.calls[-1], ("ok", "e", "input tap 189 1396"))
        self.xml = prev
        adbm.clip_overlay_dismiss("e", 33)
        self.assertEqual(self.calls[-1], ("ok", "e", "input swipe 158 1364 1060 1364 200"))
        self.xml = '<node resource-id="com.android.systemui:id/minimized_preview" class="x" bounds="[12,1604][228,1748]" />'
        adbm.clip_overlay_dismiss("e", 37)
        self.assertEqual(self.calls[-1], ("ok", "e", "input swipe 120 1676 1060 1676 200"))
        self.xml = prev
        # the overlay went away while the dump ran: no gesture on the app below
        self.calls.clear()
        self.visible = False
        adbm.clip_overlay_dismiss("e", 35)
        self.assertNotIn("ok", [c[0] for c in self.calls])
        self.calls.clear()
        self.xml = ""
        adbm.clip_overlay_dismiss("e", 33)
        adbm.clip_overlay_dismiss("e", 28)
        self.assertEqual([c[0] for c in self.calls], ["shell"])


class LocationTest(unittest.TestCase):
    def test_parse_latlon(self):
        self.assertEqual(adbm.parse_latlon("55.7558,37.6173"), (55.7558, 37.6173))
        self.assertEqual(adbm.parse_latlon(" -33.86 , 151.21 "), (-33.86, 151.21))
        with contextlib.redirect_stderr(io.StringIO()):
            for bad in ("55.7", "91,0", "0,181", "a,b"):
                with self.assertRaises(SystemExit):
                    adbm.parse_latlon(bad)

    def test_scripts(self):
        setup = adbm.location_setup_script(55.7558, 37.6173)
        self.assertIn("set-test-provider-location gps --location 55.7558,37.6173", setup)
        self.assertNotIn("; cmd", setup)  # one && chain: a failed step fails the call
        loop = adbm.location_loop_script(55.7558, 37.6173)
        # pkill -f in a command line that holds the loop's text would end that shell
        self.assertNotIn("pkill", loop)
        self.assertIn("nohup sh -c ': adbm-location-loop; while true; do appops set com.android.shell "
                      "android:mock_location allow;", loop)
        clear = adbm.location_clear_script()
        self.assertNotIn(adbm.LOCATION_LOOP, clear)
        self.assertNotIn("pkill -9", clear)
        self.assertLess(clear.index("kill -9"), clear.index("remove-test-provider"))
        self.assertIn(adbm.LOCATION_STATE, clear)

    def test_last_location(self):
        saved = adbm.ashell
        try:
            for dump, want in (("    gps provider [mock]:\n      last location=Location[gps 55.755800,37.617300 hAcc=100.0 mock]",
                                (55.7558, 37.6173, True)),
                               ("  Last Known Locations:\n    gps: Location[gps 59.938600,30.314098 hAcc=20 et=+3s]",
                                (59.9386, 30.314098, False)),
                               ("    passive provider:\n      last location=Location[gps 1.000000,2.000000 mock]\n"
                                "    gps provider:\n      last location=Location[gps 3.000000,4.000000 hAcc=5]\n",
                                (3.0, 4.0, False)),
                               ("  Last Known Locations:\n    gps: Location[gps 55,755800,37,617300 hAcc=20]",
                                (55.7558, 37.6173, False)),
                               ("      last location=null", None)):
                adbm.ashell = lambda s, cmd, timeout=60, d=dump: d
                self.assertEqual(adbm.last_location("e"), want)
        finally:
            adbm.ashell = saved


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


class StatusTest(unittest.TestCase):
    def test_calls_saved_and_project_total(self):
        run = adbm.new_run("status")
        a = type("A", (), {"cmd": "ui"})()
        for cmd, chars in (("ui", 160), ("ui", 160), ("tap", 100), ("launch", 40)):
            a.cmd = cmd
            adbm.record_context(a, chars)
        adbm.stats_add(run, context_images=1, context_image_tokens=860)
        s = adbm.context_summary(adbm.load_stats(run))
        self.assertTrue(s["calls_complete"])
        self.assertEqual(s["by_command"]["ui"], {"calls": 2, "tokens": 80})
        self.assertEqual(s["tokens"], 115 + 860)
        self.assertEqual(s["saved"], 3 * adbm.SCREEN_TOKENS - 105 + adbm.SCREEN_TOKENS - 860)
        # a command with no fresh run goes to the project cache: "outside runs"
        os.remove(os.path.join(adbm.runs_dir(), ".current"))
        adbm.USED_RUN[:] = []
        a.cmd = "devices"
        adbm.record_context(a, 40)
        proj = adbm.project_summary()
        names = [n for n, _, _ in proj["rows"]]
        self.assertIn(os.path.basename(run), names)
        self.assertIn("outside runs", names)
        self.assertEqual(proj["total"]["calls"], sum(r["calls"] for _, _, r in proj["rows"]))
        self.assertEqual(adbm.find_run("status"), run)
        self.assertEqual(adbm.find_run(os.path.basename(run)), run)
        self.assertIsNone(adbm.find_run("no-such-run"))

    def test_old_stats_without_calls(self):
        s = adbm.context_summary({"context_chars": 400, "commands": 3, "chars_by_command": {"ui": 400}})
        self.assertFalse(s["calls_complete"])
        self.assertIsNone(s["saved"])
        self.assertIsNone(s["by_command"]["ui"]["calls"])


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
        r = subprocess.run([sys.executable, hook], capture_output=True, text=True,
                           input=json.dumps({"tool_input": {"file_path": "/c/projects/p/shots/api35/1.png"}}),
                           env={**os.environ, "ADBM_CACHE": "/c"})
        self.assertIn("deny", r.stdout)

    def test_phone_avds_skip_other_form_factors(self):
        def avd(sysdir, device="pixel_8"):
            return {"api": 34, "path": "", "config": {"image.sysdir.1": sysdir, "hw.device.name": device}}
        avds = {"Television_1080p_API_34": avd("system-images/android-34/android-tv/arm64-v8a/", "tv_1080p"),
                "Pixel_Tablet_API_34": avd("system-images/android-34/google_apis/arm64-v8a/", "pixel_tablet"),
                "Wear_API_34": avd("system-images/android-34/android-wear/arm64-v8a/", "wearos_small_round"),
                "Pixel_8_API_34": avd("system-images/android-34/google_apis/arm64-v8a/"),
                "adbm_API_34": avd("system-images/android-34/google_apis/arm64-v8a/")}
        self.assertEqual(adbm.phone_avds(avds, 34), ["adbm_API_34", "Pixel_8_API_34"])
        self.assertEqual(adbm.phone_avds(avds, 35), [])

    def test_tune_keeps_bigger_values(self):
        d = tempfile.mkdtemp(dir=TMP)
        with open(os.path.join(d, "config.ini"), "w") as f:
            f.write("hw.ramSize=8192\nhw.cores=2\ndisk.dataPartition.size=16G\nhw.gpu.mode=auto\n")
        adbm.tune_config(d)
        cfg = adbm.read_ini(os.path.join(d, "config.ini"))
        self.assertEqual((cfg["hw.ramSize"], cfg["hw.cores"], cfg["disk.dataPartition.size"]), ("8192", "4", "16G"))
        self.assertEqual((cfg["hw.gpu.mode"], cfg["vm.heapSize"]), ("host", "576"))

    def test_settings_not_an_object_stops_install(self):
        cfg = tempfile.mkdtemp(dir=TMP)
        with open(os.path.join(cfg, "settings.json"), "w") as f:
            f.write("[1, 2]")
        old = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = cfg
        try:
            self.assertEqual(adbm.load_settings(), {})
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                adbm.load_settings(strict=True)
        finally:
            if old is None:
                del os.environ["CLAUDE_CONFIG_DIR"]
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = old

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

    def test_config_set_and_devices(self):
        xdg = os.path.join(TMP, "xdg2")
        proj = os.path.join(os.environ["ADBM_PROJECT"], ".adbm", "config.ini")
        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = xdg
        try:
            adbm.config_set(proj, "devices", "apis", "33, 35")
            text = open(proj).read()
            self.assertIn("\napis = 33, 35\n", text)
            self.assertIn("# model = haiku", text)  # a project file copies no values from the template
            user = os.path.join(xdg, "adbm", "config.ini")
            adbm.config_set(user, "devices", "apis", "28")
            adbm.config_set(user, "adbm-eyes", "model", "sonnet")
            cfg, problems = adbm.load_config()
            self.assertEqual(problems, [])
            self.assertEqual(cfg["devices"]["apis"], ("33, 35", "project"))
            self.assertEqual(cfg["adbm-eyes"]["model"], ("sonnet", "user"))
            adbm.config_loaded.cache_clear()
            self.assertEqual(adbm.config_apis(), [33, 35])
            adbm.config_set(proj, "devices", "apis", "")  # empty in the project: the user file decides
            self.assertEqual(adbm.load_config()[0]["devices"]["apis"], ("28", "user"))
            self.assertEqual(open(user).read().count("model ="), 1)
            self.assertEqual(adbm.check_value("devices", "apis", "28,3x")[0], None)
            self.assertEqual(adbm.check_value("devices", "apis", "35, 35,9"), ("35, 9", None))
            self.assertEqual(adbm.check_value("devices", "profile", "Nexus 5"), ("Nexus 5", None))
        finally:
            if old is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = old
            if os.path.exists(proj):
                os.remove(proj)
            adbm.config_loaded.cache_clear()

    def test_pick_uses_config_apis(self):
        devs = [{"serial": "emulator-5554", "api": 28, "emulator": True, "name": "a"},
                {"serial": "emulator-5556", "api": 35, "emulator": True, "name": "b"}]
        real = adbm.list_devices, adbm.config_apis
        adbm.list_devices = lambda: devs

        class A:
            api = serial = None
        try:
            adbm.config_apis = lambda: [28, 35]
            self.assertEqual(adbm.pick(A(), multi=True), [(28, "emulator-5554"), (35, "emulator-5556")])
            adbm.config_apis = lambda: [33, 28]  # one device: the highest running level of the list
            self.assertEqual(adbm.pick(A()), [(28, "emulator-5554")])
            adbm.config_apis = lambda: []
            self.assertEqual(adbm.pick(A()), [(35, "emulator-5556")])
        finally:
            adbm.list_devices, adbm.config_apis = real

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
