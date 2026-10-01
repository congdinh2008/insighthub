// Transport is implemented by the Python runner to share upload/retrieval oracles.
const {spawnSync} = require('node:child_process');
const path = require('node:path');
module.exports = class InsightHubProvider {
  id() { return 'insighthub-rag'; }
  async callApi(prompt, context) {
    const root=path.resolve(__dirname,'../..');
    const python=process.env.DAY6_PYTHON || path.join(root,'tmp/day6/venv/bin/python');
    const result=spawnSync(python,[path.join(root,'tools/security/day6/evaluate.py'),'case'],{
      cwd:root,input:JSON.stringify({prompt,vars:context.vars}),encoding:'utf8',timeout:150000,
      env:process.env,maxBuffer:1024*1024});
    if(result.status!==0) return {error:'Day06 runtime probe failed: '+result.stderr.slice(-200)};
    try {const row=JSON.parse(result.stdout);return {output:JSON.stringify(row),tokenUsage:row.tokenUsage};}
    catch{return {error:'Invalid runtime probe response'};}
  }
};
