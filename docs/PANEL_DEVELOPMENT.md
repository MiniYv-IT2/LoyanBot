# LoyanBot Panel Development Guide

## Project Structure

```
panel/src/
├── main.jsx                          # Entry point, BrowserRouter + AppWrapper
├── App.jsx                           # Route definitions
├── AppWrapper.jsx                    # Antd ConfigProvider + i18n locale sync
│
├── api/
│   └── index.js                      # Axios client, auth interceptor, API functions
│
├── i18n/
│   ├── index.js                      # i18next init
│   └── locales/
│       ├── zh-CN/
│       │   ├── index.ts
│       │   ├── app.ts
│       │   ├── login.ts
│       │   ├── captcha.ts
│       │   ├── lang.ts
│       │   └── dashboard.ts          # Sidebar menu, page titles
│       ├── en-US/                    # Same structure
│       ├── ru-RU/
│       ├── FR/
│       └── KO/
│
├── assets/images/
│   └── Loyan.svg
│
├── components/
│   ├── Captcha.jsx                   # CAPTCHA widget
│   ├── LanguageSelector.jsx          # Language switcher
│   └── DynamicForm/                  # Schema-driven form renderer
│       ├── index.jsx
│       └── fields/
│           ├── TextField.jsx         # type: "str"
│           ├── NumberField.jsx       # type: "int"
│           ├── BoolField.jsx         # type: "bool"
│           ├── SecretField.jsx       # type: "str" + secret: true
│           ├── SelectField.jsx       # options + labels dropdown
│           └── AdminsField.jsx       # Admin ID tag input
│
├── layouts/
│   ├── DashboardLayout.jsx           # Sidebar + Outlet + responsive drawer
│   ├── Sidebar.jsx                   # Navigation menu (fixed on desktop, drawer on mobile)
│   └── TopBar.jsx                    # Mobile hamburger trigger + breadcrumb
│
├── pages/
│   ├── Login/
│   │   └── index.jsx                 # Login page (existing)
│   │
│   └── Dashboard/
│       ├── Home/
│       │   └── index.jsx             # Dashboard overview / stats home
│       ├── Adapters/
│       │   ├── index.jsx             # Adapter list
│       │   ├── Create.jsx            # Create adapter (DynamicForm)
│       │   └── [id]/
│       │       └── Edit.jsx          # Edit adapter (DynamicForm)
│       ├── Providers/
│       │   ├── index.jsx             # Provider list
│       │   ├── Create.jsx            # Create provider (preset selector + DynamicForm)
│       │   └── [id]/
│       │       └── Edit.jsx
│       ├── AiTools/
│       │   ├── index.jsx             # Container page (SubMenu root, redirects to first child)
│       │   ├── Mcp/index.jsx
│       │   ├── Knowledge/index.jsx
│       │   ├── Memory/index.jsx
│       │   ├── Agent/index.jsx
│       │   └── Skill/index.jsx
│       ├── Logs/
│       │   └── index.jsx
│       └── Settings/
│           ├── index.jsx             # Container page
│           ├── Ai/index.jsx
│           └── General/index.jsx
│
├── stores/
│   └── useSidebarStore.js            # Sidebar collapse state (React Context or Zustand)
│
├── router/
│   └── index.jsx                     # Centralized route config
│
└── tests/                            # E2E and integration tests
```

## Page Specifications

### Login (`/login`)
Already implemented. Username + password + CAPTCHA authentication.

### Dashboard Layout (shared by all `/` routes)
- **Sidebar**: Desktop fixed 240px, collapsible to icon mode. Mobile uses Drawer with burger button in TopBar.
- **TopBar**: Mobile-only. Contains hamburger menu trigger + breadcrumb.
- **Content area**: Renders child route via `<Outlet />`.
- **Color scheme**: White background, neutral grays for text, `#8ecac8` accent for active states.

### Home (`/dashboard`)
The landing page after login. Shows:
- Welcome message
- Quick stats (total messages, active sessions, uptime)
- Adapter connection status
- Recent activity (placeholder for now)

### Adapters (`/dashboard/adapters`)
List all configured adapter instances. Each shows type (qq_official / onebot / satori), status (connected/disconnected), bot name. "Create" button opens a DynamicForm driven by adapter schema.

### Providers (`/dashboard/providers`)
List all LLM provider instances. "Create" presents a preset selector first (ChatGPT, DeepSeek, Groq...), then a DynamicForm with only ID + API Key fields (api_base is pre-filled from preset).

### AI Tools (`/dashboard/ai-tools/*`)
Container page for:
- **MCP**: MCP server configurations
- **Knowledge**: Knowledge base management
- **Memory**: Conversation memory settings
- **Agent**: AI agent configurations
- **Skill**: Skill management

### Logs (`/dashboard/logs`)
System logs viewer. Real-time or paginated log display.

### Settings (`/dashboard/settings/*`)
Container page for:
- **AI Settings**: LLM provider defaults, persona, prompt configuration
- **General**: Bot name, language, panel preferences

## Key Design Decisions

1. **DynamicForm** is the core pattern — all create/edit forms are driven by schema from `/api/loyanui/adapter/schema/:type` and `/api/loyanui/provider/schema/:type`. No hardcoded forms per adapter/provider type.

2. **Responsive**: Desktop uses fixed sidebar. Mobile uses Drawer. Same menu components, different containers.

3. **Sidebar menu** matches this structure:
   - Home
   - Adapters
   - Providers
   - AI Tools (collapsible: MCP, Knowledge, Memory, Agent, Skill)
   - Logs
   - Settings (collapsible: AI, General)

4. **i18n**: All menu labels, page titles, and form labels go through `useTranslation()`. Dashboard-specific translations in `dashboard.ts` per locale.

## Backend Dependencies

For full functionality, the panel needs these API endpoints (most already exist):

| Endpoint | Status |
|----------|--------|
| `/api/loyanui/auth/login` | ✅ |
| `/api/loyanui/auth/captcha` | ✅ |
| `/api/loyanui/auth/verify` | ✅ |
| `/api/loyanui/version` | ✅ |
| `/api/loyanui/adapter/types` | ✅ |
| `/api/loyanui/adapter/schema/:type` | ✅ |
| `/api/loyanui/instances` (GET/POST/DELETE) | ✅ |
| `/api/loyanui/providers/*` | ✅ |
| `/api/loyanui/stats` | ✅ |
