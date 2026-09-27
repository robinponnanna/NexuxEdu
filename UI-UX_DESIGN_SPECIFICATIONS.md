# UI/UX & Frontend Design Specification
## OmniCampus ERP: User Experience, Component Systems & Map Interactions

---

### 1. Design System Foundations

The design follows a modern enterprise aesthetic: clean, high-contrast, data-dense, and highly legible under bright presentation conditions.

#### 1.1. Color System
* **Primary / Institutional Indigo:** `#3B82F6` (Action items, active tabs, map route polylines)
* **Student Theme Accent (Teal):** `#0EA5E9` (Youthful, high visibility)
* **Faculty Theme Accent (Emerald):** `#10B981` (Academic authority, grading status)
* **Parent Theme Accent (Amber/Safety Orange):** `#F59E0B` (Transit tracking, security badges)
* **Admin Theme Accent (Violet):** `#8B5CF6` (System controls, database indices)
* **Surface Neutral Dark:** `#0F172A` (Background canvas for dashboards)
* **Surface Neutral Light/Card:** `#1E293B` (Elevated card panels, modal sheets)
* **Error / Restriction Red:** `#EF4444` (RBAC access denials, low attendance warnings)

#### 1.2. Typography
* **Primary Font:** Inter (`Inter, -apple-system, sans-serif`)
* **Monospace / Data Display:** JetBrains Mono (For Roll Numbers, Bus IDs, Lat/Lng coordinates)

---

### 2. Role-Based Navigation & Layout Architecture

The application layout uses an adaptive dashboard wrapper. Upon logging in, the shell changes its contextual theme and renders only authorized navigation links.

```
+-----------------------------------------------------------------------------------+
|  [Logo] OmniCampus ERP         (Role Badge: PARENT)      [Child: Alex Smith] [User|
+-------------------+---------------------------------------------------------------+
| Sidebar Nav       | Main Work Area                                                |
|                   |                                                               |
|  [x] Dashboard    |  +-------------------------------------+ +-----------------+  |
|  [x] Live Bus     |  | Live Transit Canvas (Leaflet)       | | Bus Info Card   |  |
|  [x] Attendance   |  |                                     | | Route: North-4  |  |
|  [x] AI Assistant |  |         [BUS-001]                   | | Speed: 38 km/h  |  |
|                   |  |          ●══════════○               | | Next Stop: 4m   |  |
|                   |  |                      Stop           | | Driver: Dave    |  |
|                   |  +-------------------------------------+ +-----------------+  |
+-------------------+---------------------------------------------------------------+
| Floating AI Chatbot Widget (Bottom-Right)                               [ Chat (●) ]
+-----------------------------------------------------------------------------------+
```

---

### 3. Detailed Component Designs

#### 3.1. Live Transit Visualizer (Parent Portal)
* **Map Container:** Full-height responsive canvas utilizing dark vector tiles (CartoDB DarkMatter or OpenStreetMap standard) to emphasize route visibility.
* **Bus Marker:** Custom SVG icon shaped like a transit bus with an animated CSS pulse beacon:
  ```css
  .bus-beacon {
    width: 14px;
    height: 14px;
    background: #F59E0B;
    border-radius: 50%;
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
    animation: pulse 1.6s infinite;
  }
  @keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 12px rgba(245, 158, 11, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
  }
  ```
* **Telemetry HUD Overlay:** Transparent floating card at the top-left of the map displaying:
  * Current Velocity (e.g., `36 km/h`)
  * Distance to Registered Stop (e.g., `1.4 km`)
  * Status Badge: `ON SCHEDULE` (Green) or `CONGESTION DELAY` (Red)

#### 3.2. RBAC-Grounded Chatbot Interface
* **Trigger Mechanism:** Floating Action Button (FAB) at bottom-right corner expanding into a $420\text{ px} \times 600\text{ px}$ conversation drawer.
* **Message Bubbles:**
  * User messages: Right-aligned, primary brand color.
  * System responses: Left-aligned, dark surface card with markdown support for tables and lists.
* **Source & Permission Attribution Badges:**
  * Verified Institutional Citation: Green pill label displaying `Source: Academic Regulations 2026 §4.2`.
  * RBAC Rejection State: If a student tries to query restricted records, the message bubble renders a subtle red border with an access lock icon:
    ```
    ┌─────────────────────────────────────────────────────────────┐
    │ 🔒 Restricted Access                                        │
    │ You do not have authorization to view faculty compensation  │
    │ data. This event has been logged under student session #14. │
    └─────────────────────────────────────────────────────────────┘
    ```

#### 3.3. Attendance Health Cards (Student & Faculty Views)
* Circular progress rings indicating attendance percentage:
  * $\ge 85\%$: Vibrant Emerald (`#10B981`) - "Safe Standing"
  * $75\% - 84\%$: Warning Amber (`#F59E0B`) - "Attention Required"
  * $< 75\%$: Danger Red (`#EF4444`) - "Short Attendance Debarment Warning"

---

### 4. Interactive State Workflows

#### A. Live Bus Connection Lifecycle
1. **Initial Mount:** Map loads initial static coordinates from REST endpoint `/api/v1/buses/{id}`.
2. **Socket Handshake:** Client connects to `/ws/transit/{bus_id}` with auth cookie/token.
3. **Telemetry Streaming:** Position updates arrive every 3 seconds; marker coordinates interpolate smoothly without page re-renders.
4. **Disconnection / Reconnection:** If network drops, status badge switches to `RECONNECTING...` in yellow, attempting exponential backoff reconnects without crashing the UI.

#### B. Conversational Query Lifecycle
1. User types query and hits send $\rightarrow$ Message instantly displays with typing indicator skeleton.
2. Streaming response flows token by token via Server-Sent Events (SSE) or WebSockets.
3. If an access boundary is crossed, stream terminates cleanly with standard refusal message and logs audit event.