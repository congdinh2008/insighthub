# Day 04 read-only MCP

This configuration reuses the binaries pinned and installed for Day 02. It changes only the lab endpoint and namespace:

- Prometheus: `http://127.0.0.1:19090`, query/range/targets only.
- Kubernetes: a six-hour ServiceAccount token bound to a Role in `insighthub-dev`; pods, logs, events, services and workload metadata only; Secrets denied.

After the Day 04 chart is installed and Prometheus port-forward is active:

```bash
python tools/mcp/day4/configure.py
```

Generated kubeconfig/token and host config stay under ignored `tmp/day4`. Use actual host tool calls for RCA evidence; CLI checks alone do not satisfy the MCP requirement.
