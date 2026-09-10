# KisanSense Custom Domain & Production Hosting Setup

This guide documents the configuration required to point a custom domain (e.g. `kisansense.in` or `www.kisansense.in`) to the KisanSense Streamlit application, along with root-level asset proxying for SEO.

---

## 1. Domain Architecture & Current Hosting Reality

The application is deployed on **Streamlit Community Cloud** at:
`https://kisansense-app-proto.streamlit.app`

### Streamlit Community Cloud Routing Characteristics:
1. **Dynamic Single Page Application**: All arbitrary HTTP GET routes (such as `/robots.txt` or `/sitemap.xml`) fall through to Streamlit's Starlette catch-all handler and serve `index.html`.
2. **Static Mount**: Custom static files placed in `./static/` are mounted and publicly served by Streamlit at:
   - `https://kisansense-app-proto.streamlit.app/app/static/robots.txt`
   - `https://kisansense-app-proto.streamlit.app/app/static/sitemap.xml`
   - `https://kisansense-app-proto.streamlit.app/app/static/llms.txt`
   - `https://kisansense-app-proto.streamlit.app/app/static/favicon.png`
   - `https://kisansense-app-proto.streamlit.app/app/static/og-image.png`

---

## 2. Setting Up `kisansense.in` on Streamlit Community Cloud

To map `kisansense.in` and `www.kisansense.in`:

### Step A: Streamlit Community Cloud Dashboard
1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Locate the `KisanSense-app-proto` application.
3. Open **Settings** &rarr; **Custom domain**.
4. Enter `kisansense.in` (or `www.kisansense.in`).
5. Note the target CNAME provided by Streamlit (typically `[subdomain].streamlit.app` or Streamlit's routing edge).

### Step B: DNS Record Configuration (at Domain Registrar / DNS Provider)

Configure the following DNS records:

| Type | Name | Target / Content | Proxy Status | TTL |
| :--- | :--- | :--- | :--- | :--- |
| **CNAME** | `www` | `kisansense-app-proto.streamlit.app` | DNS Only (or Proxied if Cloudflare) | Auto |
| **CNAME** / **ALIAS** | `@` (apex) | `kisansense-app-proto.streamlit.app` | CNAME Flattening (Cloudflare) | Auto |

> [!NOTE]
> Apex domains (`@` / `kisansense.in`) cannot use standard CNAME records according to RFC 1034. Use a DNS provider with **CNAME Flattening** or **ALIAS/ANAME** support (such as Cloudflare, DNSimple, or Route53).

---

## 3. Root-Level SEO Reverse Proxy Configuration (Cloudflare Worker or Nginx)

Because search engine crawlers expect `/robots.txt` and `/sitemap.xml` at the root domain (`https://kisansense.in/robots.txt`), configure an edge rewrite rule:

### Option A: Cloudflare Worker / Transform Rule

When using Cloudflare as the DNS and CDN edge:

```javascript
// Cloudflare Worker: route https://kisansense.in/robots.txt and /sitemap.xml
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    if (url.pathname === "/robots.txt") {
      url.pathname = "/app/static/robots.txt";
      return fetch(url.toString(), request);
    }
    if (url.pathname === "/sitemap.xml") {
      url.pathname = "/app/static/sitemap.xml";
      return fetch(url.toString(), request);
    }
    if (url.pathname === "/llms.txt") {
      url.pathname = "/app/static/llms.txt";
      return fetch(url.toString(), request);
    }

    return fetch(request);
  }
};
```

### Option B: Nginx Reverse Proxy (Self-Hosted / VPS)

If hosting behind an Nginx reverse proxy:

```nginx
server {
    server_name kisansense.in www.kisansense.in;

    location = /robots.txt {
        proxy_pass http://127.0.0.1:8501/app/static/robots.txt;
        proxy_set_header Host $host;
    }

    location = /sitemap.xml {
        proxy_pass http://127.0.0.1:8501/app/static/sitemap.xml;
        proxy_set_header Host $host;
    }

    location = /llms.txt {
        proxy_pass http://127.0.0.1:8501/app/static/llms.txt;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 4. Environment Variable Configuration

To switch canonical URLs to your custom domain, set the environment variable:

```bash
KISANSENSE_BASE_URL="https://kisansense.in"
```

In Streamlit Community Cloud:
Add `KISANSENSE_BASE_URL = "https://kisansense.in"` to **App settings** &rarr; **Secrets**.
