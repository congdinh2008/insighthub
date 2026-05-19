import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { fixture, CANARY } from './fixture.mjs';
import { connectClient } from './client.mjs';

async function denied(client, name, args) {
  // request() bypasses the SDK callTool helper's local schema cache. The
  // registered server handler/dispatch must reject the actual wire request.
  try {
    const response = await client.request({method:'tools/call',params:{name,arguments:args}});
    assert.equal(response.isError,true);
  } catch (error) {
    if (error instanceof assert.AssertionError) throw error;
    assert.ok(typeof error.code === 'number', 'Expected MCP protocol rejection');
  }
}
for (const mode of ['modern','legacy']) {
  test(mode + ': server allowlist cannot be bypassed through direct tools/call', async t => {
    const f = await fixture();t.after(f.close);
    const s = await connectClient(mode,{INSIGHTHUB_API_URL:f.url,INSIGHTHUB_MCP_TOOLS:'insighthub_health'});
    t.after(() => s.client.close());
    const list = await s.client.listTools();
    assert.deepEqual(list.tools.map(t => t.name),['insighthub_health']);
    assert.equal(list.tools[0].annotations.readOnlyHint,true);
    for (const [name,args] of [
      ['insighthub_list_documents',{}],['prometheus_summary',{query:'documents'}],
      ['delete_document',{id:1}],['shell',{command:'touch '+CANARY}],['read_file',{path:'/etc/passwd'}],
      [CANARY,{}],['insighthub_health',{url:'http://169.254.169.254'}],
      ['insighthub_health',{[CANARY]:true}],
    ]) await denied(s.client,name,args);
    assert.equal(f.requests.length,0);
    const good = await s.client.callTool({name:'insighthub_health',arguments:{}});
    assert.notEqual(good.isError,true);
    const received = s.wire.filter(w => w.direction === 'in');
    assert.ok(!JSON.stringify(received).includes(CANARY));
    assert.equal(s.stderr(),'');
  });
  test(mode + ': list bounds and arbitrary PromQL are rejected by server', async t => {
    const f = await fixture();t.after(f.close);
    const s = await connectClient(mode,{INSIGHTHUB_API_URL:f.url,INSIGHTHUB_PROMETHEUS_URL:f.url,
      INSIGHTHUB_MCP_PROMETHEUS:'1',INSIGHTHUB_MCP_TOOLS:'insighthub_list_documents,prometheus_summary'});
    t.after(() => s.client.close());
    await s.client.listTools();
    for(const args of [{limit:0},{limit:21},{limit:1.2},{limit:'2'},{limit:2,content:true}])
      await denied(s.client,'insighthub_list_documents',args);
    await denied(s.client,'prometheus_summary',{query:'sum_over_time(up[365d])'});
    await denied(s.client,'prometheus_summary',{query:'documents',endpoint:'/api/v1/admin/tsdb/delete_series'});
    assert.equal(f.requests.length,0);
  });
}
test('empty allowlist exposes no tools and denies direct invocation', async t => {
  const f=await fixture();t.after(f.close);
  const s=await connectClient('modern',{INSIGHTHUB_API_URL:f.url,INSIGHTHUB_MCP_TOOLS:''});
  t.after(()=>s.client.close());
  assert.deepEqual((await s.client.listTools()).tools,[]);
  await denied(s.client,'insighthub_health',{});
  assert.equal(f.requests.length,0);
});
test('invalid endpoint exits without reflecting a credential on stderr/stdout', async () => {
  const child=spawn(process.execPath,[fileURLToPath(new URL('../src/server.mjs',import.meta.url))],
    {env:{INSIGHTHUB_API_URL:'http://'+CANARY+'@example.org'},stdio:['pipe','pipe','pipe']});
  let output='';
  child.stdout.on('data',d=>output+=d);child.stderr.on('data',d=>output+=d);
  const code=await new Promise((resolve,reject)=>{child.on('exit',resolve);child.on('error',reject);});
  assert.equal(code,1);assert.ok(!output.includes(CANARY));assert.ok(output.includes('MCP_STARTUP_REJECTED'));
});
