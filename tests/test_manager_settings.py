import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from manager import server

class ManagerSettingsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.content=self.root/'projects.json';self.content.write_text(server.CONTENT_PATH.read_text())
  self.patches=[patch.object(server,'CONTENT_PATH',self.content),patch.object(server,'BACKUP_DIR',self.root/'backups')]
  for p in self.patches:p.start()
  self.client=server.app.test_client();self.headers={'X-Portfolio-Token':server.TOKEN}
 def tearDown(self):
  for p in self.patches:p.stop()
  self.temp.cleanup()
 def test_settings_roundtrip_and_invalid_path(self):
  settings=self.client.get('/api/settings').json['settings']
  settings['categoryCards']['production']['role']={'en':'Producer test','zh':'制片测试'}
  settings['site']['labels']['en']['back']='Return'
  self.assertEqual(self.client.post('/api/settings',json=settings,headers=self.headers).status_code,200)
  self.assertEqual(self.client.get('/api/settings').json['settings'],settings)
  settings['categoryCards']['production']['cover']='assets/../../private.png'
  self.assertEqual(self.client.post('/api/settings',json=settings,headers=self.headers).status_code,400)
 def test_project_text_save_preserves_layout(self):
  original=json.loads(self.content.read_text())['categories'][0]['projects'][0]
  p=self.client.get('/api/projects').json['projects'][0]
  p.update(role={'en':'Director test','zh':'导演'},date={'en':'Present','zh':'至今'},year='',month='',galleryChanged=False,videosChanged=False)
  r=self.client.post('/api/projects/save',data={'payload':json.dumps(p)},headers=self.headers)
  self.assertEqual(r.status_code,200,r.json)
  saved=json.loads(self.content.read_text())['categories'][0]['projects'][0]
  self.assertEqual(saved['rows'],original['rows']);self.assertEqual(saved['date']['en'],'Present');self.assertEqual(saved['role'],p['role'])
 def test_auth_required(self):
  self.assertEqual(self.client.post('/api/settings',json={}).status_code,403)
if __name__=='__main__':unittest.main()
