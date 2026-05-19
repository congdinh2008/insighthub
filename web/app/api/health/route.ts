// InsightHub Web — health endpoint cho K8s probe / Docker HEALTHCHECK
export async function GET() {
  return Response.json({ status: "ok", service: "insighthub-web" });
}
