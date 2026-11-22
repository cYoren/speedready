#!/usr/bin/env python3
"""The desktop sender: nothing goes out when the key is empty or the switch is off, and what does go
out carries the app name and no free-form property. Run: python3 tests/test_posthog.py"""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import posthog

class Fake:
    def __init__(s):s.sent=[]
    def __call__(s,body):s.sent.append(body)

class Analytics(unittest.TestCase):
    def make(s,key=posthog.KEY,enabled=True,send=None):
        tmp=tempfile.TemporaryDirectory();s.addCleanup(tmp.cleanup)
        return posthog.Analytics(Path(tmp.name)/'analytics.json','1.0.10',locale='pt',
                                 is_enabled=lambda:enabled,key=key,send=send or Fake())
    def batch(s,a):
        import time
        for _ in range(40):                     # the POST runs on a daemon thread: let it land
            if a.send.sent:break
            time.sleep(0.01)
        return a.send.sent
    def test_empty_key_sends_nothing(s):
        a=s.make(key='');a.track('app_opened');a.opt_out()
        s.assertEqual(s.batch(a),[])
    def test_switch_off_sends_nothing(s):
        a=s.make(enabled=False);a.track('reading_session_completed',wpm_bucket='250_399',minutes_bucket='5_14')
        s.assertEqual(s.batch(a),[])
    def test_payload_is_anonymous(s):
        a=s.make();a.track('reading_session_completed',wpm_bucket='250_399',minutes_bucket='5_14',
                           title='Der Prozess',text='hello',note='x')
        body=s.batch(a)[0];event=body['batch'][0];props=event['properties']
        s.assertEqual(body['api_key'],posthog.KEY)
        s.assertEqual(event['event'],'reading_session_completed')
        for key in('app','platform','app_version','locale','$process_person_profile'):
            s.assertIn(key,props)
        s.assertEqual(props['app'],'speedready')
        s.assertEqual(props['locale'],'pt')
        s.assertNotIn('title',props);s.assertNotIn('text',props);s.assertNotIn('note',props)
        s.assertEqual(props['wpm_bucket'],'250_399')
    def test_opt_out_is_sent_before_the_switch_off(s):
        a=s.make();a.opt_out()
        events=[e for body in s.batch(a) for e in body['batch']]
        s.assertEqual([e['event'] for e in events],['settings_analytics_opt_out'])
    def test_first_value_only_once(s):
        a=s.make();a.first_value(wpm_bucket='150_249');a.first_value(wpm_bucket='150_249')
        events=[e['event'] for body in s.batch(a) for e in body['batch']]
        s.assertEqual(events,['first_value'])
        s.assertEqual(json.loads(a.path.read_text())['first_value'],True)

if __name__=='__main__':unittest.main()
