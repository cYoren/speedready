"""The release guard in tools/check_release_tag.py: a tag has to bump Android's versionCode."""
import sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import check_release_tag as guard

class ReleaseTagTests(unittest.TestCase):
    def test_a_tag_that_does_not_bump_versioncode_is_rejected(self):
        self.assertEqual(guard.errors('v1.1.0','1.1.0',9,'v1.0.9',8),[])
        problems=guard.errors('v1.0.9','1.0.9',8,'v1.0.8',8)
        self.assertTrue(any('did not increase' in p for p in problems))
    def test_the_tag_and_versionname_must_agree(self):
        self.assertTrue(any('does not match' in p for p in guard.errors('v1.0.9','1.0.8',9,'v1.0.8',8)))
    def test_parsers(self):
        self.assertEqual(guard.gradle_version("versionCode 12\nversionName '1.2.0'"),(12,'1.2.0'))
        _,name=guard.gradle_version((ROOT/guard.GRADLE).read_text())
        self.assertRegex(name,r'^\d+\.\d+\.\d+$')
        meta=guard.metadata_state((ROOT/guard.METADATA).read_text())
        self.assertIsInstance(meta[1],int);self.assertRegex(meta[2],r'^[0-9a-f]{40}$')
        self.assertRegex(meta[0],r'^\d+\.\d+\.\d+$')   # versionName is the first field of the entry: it must survive the split
        text='Builds:\n  - versionName: 1.0.6\n    versionCode: 6\n    commit: '+'a'*40+'\n  - versionName: 1.0.7\n    versionCode: 7\n    commit: '+'b'*40+'\n    subdir: x\n'
        self.assertEqual(guard.metadata_state(text),('1.0.7',7,'b'*40))
    def test_strict_mode_accepts_metadata_that_matches_the_tag(self):
        self.assertEqual(guard.errors('v1.0.7','1.0.7',7,'v1.0.6',6,('1.0.7',7,'b'*40),True,'b'*40),[])
    def test_strict_mode_reports_metadata_that_is_behind_the_tag(self):
        problems=guard.errors('v1.0.8','1.0.8',8,'v1.0.7',7,('1.0.7',7,'a'*40),True,'b'*40)
        self.assertEqual(len(problems),2,problems)
    @unittest.skipUnless((ROOT/'.git').exists(),'not a git checkout')
    def test_strict_compares_against_the_commit_an_annotated_tag_points_at(self):
        # `git rev-parse v1.0.9` returns the tag object for an annotated tag, and that is never the
        # commit fdroiddata checks out: strict mode has to resolve the commit, or it can never pass.
        annotated=[t for t in guard.git('tag','-l','v*').split() if guard.git('cat-file','-t',t)=='tag']
        self.assertTrue(annotated,'expected the repository to keep annotated release tags')
        for tag in annotated:
            self.assertEqual(guard.commit_at(tag),guard.git('rev-list','-n','1',tag),tag)
            self.assertNotEqual(guard.commit_at(tag),guard.git('rev-parse',tag),tag)
    @unittest.skipUnless((ROOT/'.git').exists(),'not a git checkout')
    def test_history_only_trips_on_the_release_that_forgot_the_bump(self):
        tags=guard.git('tag','-l','v*','--sort=v:refname').split()
        failed={t:guard.check(t,verbose=False) for t in tags if guard.check(t,verbose=False)}
        # v1.0.2 shipped with versionName 1.0.1 and versionCode 2: the mistake this guard exists to stop.
        self.assertEqual(list(failed),['v1.0.2'])

if __name__=='__main__':unittest.main()
