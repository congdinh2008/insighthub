"""Runtime settings; credentials only come from environment or protected files."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    signing_secret: str
    bot_token: str
    app_id: str
    workspace_id: str
    bot_user_id: str
    channel_id: str
    approver_user_id: str
    redis_url: str
    api_url: str
    mcp_config: str
    audit_path: str
    kubeconfig_scale: str
    model_url: str
    model_name: str
    model_key: str
    namespace: str = "insighthub-dev"
    cluster_context: str = "kind-insighthub-local"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
            bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
            app_id=os.getenv("SLACK_APP_ID", "A0C3EU2GD35"),
            workspace_id=os.getenv("SLACK_WORKSPACE_ID", "T0C35P86Z1D"),
            bot_user_id=os.getenv("SLACK_BOT_USER_ID", ""),
            channel_id=os.getenv("CHATOPS_CHANNEL_ID", ""),
            approver_user_id=os.getenv("CHATOPS_APPROVER_USER_ID", ""),
            redis_url=os.getenv("CHATOPS_REDIS_URL", "redis://127.0.0.1:16379/0"),
            api_url=os.getenv("CHATOPS_API_URL", "http://127.0.0.1:18000"),
            mcp_config=os.getenv("CHATOPS_MCP_CONFIG", ""),
            audit_path=os.getenv("CHATOPS_AUDIT_PATH", "/tmp/chatops-audit.log"),
            kubeconfig_scale=os.getenv("CHATOPS_SCALE_KUBECONFIG", ""),
            model_url=os.getenv("CHATOPS_MODEL_URL", ""),
            model_name=os.getenv("CHATOPS_MODEL_NAME", ""),
            model_key=os.getenv("CHATOPS_MODEL_KEY", ""),
        )
