#!/usr/bin/env python3
"""Release guard: a tag that does not bump Android's versionCode never reaches Android users.

    python tools/check_release_tag.py             # the tag at HEAD
    python tools/check_release_tag.py v1.0.9     # a specific tag
    python tools/check_release_tag.py --strict   # also require the fdroiddata metadata to match

F-Droid's updater compares versionCode, not tags (`UpdateCheckMode: Tags`). A release whose
versionCode did not increase is found and then correctly ignored, so it silently never arrives.
tools/make_release_apk.sh runs this before building; tests/test_release_tag.py runs it over the
repository's own tag history.
"""
import re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
GRADLE='android/app/build.gradle'
METADATA='android/fdroid/io.github.cyoren.speedready.yml'

def gradle_version(text):
    code=re.search(r'versionCode\s+(\d+)',text);name=re.search(r"versionName\s+'([^']+)'",text)
    if not code or not name:raise ValueError(f'no versionCode/versionName in {GRADLE}')
    return int(code[1]),name[1]

def metadata_state(text):
    """(versionName, versionCode, commit) of the last fdroiddata build entry: what F-Droid will check out."""
    build=text.rsplit('- versionName:',1)
    if len(build)<2:return None
    entry=build[1]
    def field(key):
        m=re.search(rf'^\s*{key}:\s*(\S+)\s*$',entry,re.M);return m[1].strip("'\"") if m else None
    name,code,commit=field('versionName'),field('versionCode'),field('commit')
    return (name,int(code) if code and code.isdigit() else None,commit)

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()

def tag_at_head():
    try:return git('describe','--tags','--exact-match','HEAD')
    except subprocess.CalledProcessError:return None

def versions_at(tag):
    return gradle_version(git('show',f'{tag}:{GRADLE}'))

def previous_tag(tag):
    try:return git('describe','--tags','--abbrev=0','--match','v*',f'{tag}^')
    except subprocess.CalledProcessError:return None

def errors(tag,name,code,prev_tag=None,prev_code=None,meta=None,strict=False,commit=None):
    """The rules, as a pure function: the tests can hold each one to its message."""
    out=[]
    if tag.lstrip('v')!=name:out.append(f'tag {tag} does not match versionName {name} in {GRADLE}')
    if prev_code is not None and code<=prev_code:
        out.append(f'versionCode {code} did not increase from {prev_code} at {prev_tag}: F-Droid\'s Tags updater would skip {tag}')
    if strict:
        if meta is None:out.append(f'{METADATA} has no build entry to compare')
        else:
            mname,mcode,mcommit=meta
            if (mname,mcode)!=(name,code):out.append(f'{METADATA} says {mname}/{mcode}, the tag says {name}/{code}')
            if mcommit and commit and not commit.startswith(mcommit):out.append(f'{METADATA} commit {mcommit} is not {tag}')
    return out

def check(tag=None,strict=False,verbose=True):
    tag=tag or tag_at_head()
    if not tag:return ['HEAD is not tagged: bump the version, commit, then tag it (git tag -a v<version>)']
    try:code,name=versions_at(tag)
    except (subprocess.CalledProcessError,ValueError) as e:return [f'{tag} does not carry {GRADLE}: {e}']
    prev=previous_tag(tag);prev_code=None
    if prev:
        try:prev_code=versions_at(prev)[0]
        except (subprocess.CalledProcessError,ValueError):pass
    meta=None
    if strict and (ROOT/METADATA).exists():meta=metadata_state((ROOT/METADATA).read_text())
    commit=git('rev-parse',tag)
    out=errors(tag,name,code,prev,prev_code,meta,strict,commit)
    if not out and verbose:print(f'{tag}: versionName {name}, versionCode {code}'+(f' > {prev_code} at {prev}' if prev_code else '')+'  ok')
    return out

if __name__=='__main__':
    args=[a for a in sys.argv[1:] if not a.startswith('-')]
    problems=check(args[0] if args else None,'--strict' in sys.argv)
    for p in problems:print(p,file=sys.stderr)
    sys.exit(1 if problems else 0)
