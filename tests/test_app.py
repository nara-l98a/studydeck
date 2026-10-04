import json, tempfile, unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from studydeck.app import main, load_data

class StudyDeckTests(unittest.TestCase):
    def run_cli(self, path, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err): code=main(["--data", str(path), *args])
        return code, out.getvalue(), err.getvalue()
    def test_add_persists_card_and_tags(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"; code, out, _=self.run_cli(p,"add","TCP","传输控制协议","--tags","网络,协议")
            self.assertEqual(code,0); obj=load_data(p); self.assertEqual(obj["cards"]["1"]["tags"],["协议","网络"])
    def test_review_updates_interval_and_due(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"; self.run_cli(p,"add","a","b"); code,out,_=self.run_cli(p,"review","1","5")
            self.assertEqual(code,0); c=load_data(p)["cards"]["1"]; self.assertEqual(c["interval"],3); self.assertEqual(c["reviews"],1)
    def test_invalid_rating_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"; self.run_cli(p,"add","a","b"); code,_,err=self.run_cli(p,"review","1","6")
            self.assertNotEqual(code,0); self.assertIn("0 到 5",err); self.assertEqual(load_data(p)["cards"]["1"]["reviews"],0)
    def test_due_filter_and_stats(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"; self.run_cli(p,"add","a","b","--tags","math"); _,out,_=self.run_cli(p,"list","--due","--tag","math"); self.assertIn("1 张卡片",out)
            _,stats,_=self.run_cli(p,"stats"); self.assertIn("卡片总数：1",stats)
    def test_missing_card_errors(self):
        with tempfile.TemporaryDirectory() as d:
            code,_,err=self.run_cli(Path(d)/"x.json","review","nope","3"); self.assertEqual(code,2); self.assertIn("找不到",err)
    def test_stats_average_latest_ratings_not_total_review_count(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"
            self.run_cli(p,"add","a","b")
            self.run_cli(p,"review","1","5")
            self.run_cli(p,"review","1","5")
            self.run_cli(p,"add","c","d")
            self.run_cli(p,"review","2","1")
            _,stats,_=self.run_cli(p,"stats")
            self.assertIn("复习次数：3",stats)
            self.assertIn("最近评分均值：3.00",stats)
    def test_malformed_card_is_reported_without_overwriting_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cards.json"
            p.write_text(json.dumps({"version": 1, "cards": {"1": {"front": "a", "back": "b", "difficulty": "hard"}}}), encoding="utf-8")
            original = p.read_text(encoding="utf-8")
            code,_,err=self.run_cli(p,"list")
            self.assertEqual(code,2)
            self.assertIn("difficulty",err)
            self.assertEqual(p.read_text(encoding="utf-8"), original)
if __name__ == "__main__": unittest.main()
