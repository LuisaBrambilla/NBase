(function () {
  const DEFAULT_REMOTE_API = "https://app-gen360-api.azurewebsites.net";
  const host = window.location.hostname || "";
  const protocol = window.location.protocol || "";
  const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(host);
  const isFileProtocol = protocol === "file:";
  const isAzureStatic = /\.web\.core\.windows\.net$/i.test(host);

  let configured = (window.API_BASE_URL || "").trim();

  if (!configured) {
    configured = isLocalHost || isFileProtocol ? "http://localhost:8000" : DEFAULT_REMOTE_API;
  }

  if (configured.startsWith("/")) {
    if (isLocalHost && window.location.origin) {
      configured = `${window.location.origin}${configured}`;
    } else {
      configured = DEFAULT_REMOTE_API;
    }
  }

  if (isAzureStatic && !isLocalHost) {
    configured = DEFAULT_REMOTE_API;
  }

  window.API_BASE_URL = configured.replace(/\/+$/, "");
})();
