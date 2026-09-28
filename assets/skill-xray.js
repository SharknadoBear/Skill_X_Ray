(function () {
  "use strict";

  const TYPE_META = {
    working_state: { prefix: "W", label: "Working states" },
    gate_collection: { prefix: "G", label: "Gate collections" },
    tool: { prefix: "T", label: "Tools and scripts" },
    example: { prefix: "E", label: "Heuristic examples" },
    skill_call: { prefix: "S", label: "Inter-skill calls" }
  };
  const MAIN_TYPES = new Set(["working_state", "gate_collection", "skill_call"]);
  const MAIN_EDGES = new Set(["flow", "gate_advance", "gate_iterate", "gate_finish", "skill_invoke", "skill_return"]);
  const LAYOUT_MODES = ["LR", "TB", "RADIAL"];
  const LEAF_URI = "__LEAF_DATA_URI__";
  const selfTestMode = new URLSearchParams(window.location.search).get("selftest") === "1";
  const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function decodeGraph() {
    const encoded = document.getElementById("xray-data").textContent.trim();
    const raw = atob(encoded);
    const bytes = Uint8Array.from(raw, character => character.charCodeAt(0));
    return JSON.parse(new TextDecoder("utf-8").decode(bytes));
  }

  function make(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }

  function safeHref(value) {
    if (typeof value !== "string" || !value || /[\u0000-\u001f]/.test(value)) return false;
    if (/^https:\/\//i.test(value)) return true;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value) || /^[/\\]/.test(value) || /^[A-Za-z]:/.test(value)) return false;
    return true;
  }

  function palette() {
    const style = getComputedStyle(document.documentElement);
    const read = name => style.getPropertyValue(name).trim();
    return {
      ink: read("--ink"), panel: read("--panel"), line: read("--line"), accent: read("--accent"),
      focus: read("--focus"), working: read("--working"), workingBorder: read("--working-border"),
      terminalWorking: read("--terminal-working"), terminalWorkingBorder: read("--terminal-working-border"),
      tool: read("--tool"), example: read("--example"), gate: read("--gate"), skill: read("--skill")
    };
  }

  function boot() {
    const graph = decodeGraph();
    const nodesById = new Map(graph.nodes.map(node => [node.id, node]));
    const edgesById = new Map(graph.edges.map(edge => [edge.id, edge]));
    const mainNodeCount = graph.nodes.filter(node => MAIN_TYPES.has(node.type)).length;
    let layoutMode = mainNodeCount >= 15 ? "RADIAL" : "LR";
    let pinnedId = null;
    let radialEnvelope = null;

    document.getElementById("skill-name").textContent = graph.skill.name;
    document.getElementById("skill-description").textContent = graph.skill.description;
    document.getElementById("generated-at").textContent = graph.skill.generated_at;
    document.getElementById("source-path").textContent = graph.skill.source_path;
    document.title = graph.skill.name + " — Skill X-Ray";

    const elements = [];
    graph.nodes.forEach(node => elements.push({
      group: "nodes",
      data: {
        id: node.id,
        label: node.id,
        type: node.type,
        terminal: node.terminal === true,
        title: node.title
      }
    }));
    graph.edges.forEach(edge => elements.push({
      group: "edges",
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        condition: edge.condition || ""
      }
    }));

    const colors = palette();
    const cy = cytoscape({
      container: document.getElementById("graph-canvas"),
      elements: elements,
      minZoom: 0.08,
      maxZoom: 4,
      wheelSensitivity: 0.18,
      boxSelectionEnabled: false,
      style: [
        { selector: "node", style: {
          "label": "data(label)", "font-family": "Segoe UI, sans-serif", "font-size": 12,
          "font-weight": 800, "text-valign": "center", "text-halign": "center",
          "color": colors.ink, "background-color": colors.working, "border-color": colors.workingBorder,
          "border-width": 2, "width": 48, "height": 48, "shape": "ellipse",
          "text-outline-width": 0, "overlay-opacity": 0
        }},
        { selector: "node[type = 'working_state'][?terminal]", style: {
          "background-color": colors.terminalWorking, "border-color": colors.terminalWorkingBorder, "border-width": 4
        }},
        { selector: "node[type = 'tool']", style: {
          "shape": "ellipse", "width": 26, "height": 26, "background-color": colors.tool,
          "border-color": colors.panel, "border-width": 2, "color": colors.panel, "font-size": 9
        }},
        { selector: "node[type = 'example']", style: {
          "shape": "rectangle", "width": 38, "height": 28, "background-opacity": 0,
          "background-image": LEAF_URI, "background-fit": "contain", "background-clip": "none",
          "border-width": 0, "color": colors.ink, "font-size": 9
        }},
        { selector: "node[type = 'gate_collection']", style: {
          "shape": "diamond", "width": 48, "height": 48, "background-color": colors.gate,
          "border-color": "#75550b", "border-width": 2, "font-size": 10
        }},
        { selector: "node[type = 'skill_call']", style: {
          "shape": "ellipse", "width": 66, "height": 66, "background-color": colors.skill,
          "border-color": "#433788", "border-width": 3, "color": "#ffffff", "font-size": 11
        }},
        { selector: "edge", style: {
          "curve-style": "bezier", "width": 2.1, "line-color": "#64798b",
          "target-arrow-color": "#64798b", "target-arrow-shape": "triangle", "arrow-scale": 1,
          "label": "", "font-size": 10, "text-background-color": colors.panel,
          "text-background-opacity": .92, "text-background-padding": 3, "color": colors.ink,
          "overlay-opacity": 0
        }},
        { selector: "edge[type = 'tool_support']", style: { "width": 1.2, "line-color": "#8a9aa8", "target-arrow-color": "#8a9aa8" } },
        { selector: "edge[type = 'example_guidance']", style: { "line-style": "dashed", "width": 1.2, "line-color": colors.example, "target-arrow-color": colors.example } },
        { selector: "edge[type = 'skill_invoke']", style: { "width": 3, "line-color": colors.skill, "target-arrow-color": colors.skill } },
        { selector: "edge[type = 'gate_finish']", style: { "width": 3 } },
        { selector: "edge[type = 'gate_iterate']", style: { "curve-style": "unbundled-bezier", "control-point-distances": -75, "control-point-weights": .45 } },
        { selector: ".dimmed", style: { "opacity": .14 } },
        { selector: ".focused", style: { "opacity": 1, "border-color": colors.focus, "border-width": 4, "line-color": colors.focus, "target-arrow-color": colors.focus, "z-index": 999 } },
        { selector: ".edge-label", style: { "label": "data(condition)", "text-rotation": "autorotate", "text-margin-y": -8 } },
        { selector: ".filtered", style: { "display": "none" } }
      ]
    });

    function averagePosition(collection) {
      if (!collection.length) return { x: 0, y: 0 };
      const total = collection.reduce((sum, node) => ({ x: sum.x + node.position("x"), y: sum.y + node.position("y") }), { x: 0, y: 0 });
      return { x: total.x / collection.length, y: total.y / collection.length };
    }

    function collides(position, node, placed) {
      for (const other of placed) {
        if (other.id() === node.id()) continue;
        const op = other.position();
        const minimum = collisionRadius(node) + collisionRadius(other) + 8;
        if (Math.hypot(position.x - op.x, position.y - op.y) < minimum) return true;
      }
      return false;
    }

    function stableAngle(identifier) {
      let hash = 2166136261;
      for (const character of identifier) {
        hash ^= character.charCodeAt(0);
        hash = Math.imul(hash, 16777619);
      }
      return ((hash >>> 0) / 4294967296) * Math.PI * 2;
    }

    function radialUnit(anchor, center, identifier) {
      const dx = anchor.x - center.x;
      const dy = anchor.y - center.y;
      const length = Math.hypot(dx, dy);
      if (length > 1) return { x: dx / length, y: dy / length };
      const angle = stableAngle(identifier);
      return { x: Math.cos(angle), y: Math.sin(angle) };
    }

    function placeRadialSupportNodes() {
      const mainNodes = cy.nodes().filter(node => MAIN_TYPES.has(node.data("type")));
      const center = averagePosition(mainNodes);
      const placed = mainNodes.toArray();
      const toolsByAnchor = new Map();
      cy.nodes("[type = 'tool']").sort((a, b) => a.id().localeCompare(b.id(), undefined, { numeric: true })).forEach(tool => {
        const targets = tool.outgoers("edge[type = 'tool_support']").targets();
        const key = targets.map(node => node.id()).sort().join("|") || "unattached";
        if (!toolsByAnchor.has(key)) toolsByAnchor.set(key, []);
        toolsByAnchor.get(key).push({ tool, targets });
      });
      toolsByAnchor.forEach(group => {
        group.forEach((entry, index) => {
          const anchor = entry.targets.length ? averagePosition(entry.targets) : center;
          const radial = radialUnit(anchor, center, entry.tool.id());
          const tangent = { x: -radial.y, y: radial.x };
          const spread = (index - (group.length - 1) / 2) * 42;
          let offset = 76;
          let position = {
            x: anchor.x + radial.x * offset + tangent.x * spread,
            y: anchor.y + radial.y * offset + tangent.y * spread
          };
          let attempts = 0;
          while (collides(position, entry.tool, placed) && attempts < 18) {
            offset += 22;
            position = {
              x: anchor.x + radial.x * offset + tangent.x * spread,
              y: anchor.y + radial.y * offset + tangent.y * spread
            };
            attempts += 1;
          }
          entry.tool.position(position);
          placed.push(entry.tool);
        });
      });
      const examplesByTool = new Map();
      cy.nodes("[type = 'example']").sort((a, b) => a.id().localeCompare(b.id(), undefined, { numeric: true })).forEach(example => {
        const tool = example.outgoers("edge[type = 'example_guidance']").targets().first();
        if (!tool || tool.empty()) return;
        if (!examplesByTool.has(tool.id())) examplesByTool.set(tool.id(), []);
        examplesByTool.get(tool.id()).push({ example, tool });
      });
      examplesByTool.forEach(group => {
        group.forEach((entry, index) => {
          const anchor = entry.tool.position();
          const radial = radialUnit(anchor, center, entry.example.id());
          const tangent = { x: -radial.y, y: radial.x };
          const spread = (index - (group.length - 1) / 2) * 36;
          let offset = 58;
          let position = {
            x: anchor.x + radial.x * offset + tangent.x * spread,
            y: anchor.y + radial.y * offset + tangent.y * spread
          };
          let attempts = 0;
          while (collides(position, entry.example, placed) && attempts < 18) {
            offset += 20;
            position = {
              x: anchor.x + radial.x * offset + tangent.x * spread,
              y: anchor.y + radial.y * offset + tangent.y * spread
            };
            attempts += 1;
          }
          entry.example.position(position);
          placed.push(entry.example);
        });
      });
    }

    function placeSupportNodes() {
      if (layoutMode === "RADIAL") {
        placeRadialSupportNodes();
        return;
      }
      const placed = cy.nodes().filter(node => MAIN_TYPES.has(node.data("type"))).toArray();
      const toolsByAnchor = new Map();
      cy.nodes("[type = 'tool']").sort((a, b) => a.id().localeCompare(b.id())).forEach(tool => {
        const targets = tool.outgoers("edge[type = 'tool_support']").targets();
        const key = targets.map(node => node.id()).sort().join("|") || "unattached";
        if (!toolsByAnchor.has(key)) toolsByAnchor.set(key, []);
        toolsByAnchor.get(key).push({ tool, targets });
      });
      toolsByAnchor.forEach(group => {
        group.forEach((entry, index) => {
          const anchor = averagePosition(entry.targets);
          const side = index % 2 === 0 ? -1 : 1;
          const lane = Math.floor(index / 2);
          let position = layoutMode === "LR"
            ? { x: anchor.x + (lane - (group.length / 4)) * 42, y: anchor.y + side * (78 + lane * 19) }
            : { x: anchor.x + side * (88 + lane * 19), y: anchor.y + (lane - (group.length / 4)) * 42 };
          let attempts = 0;
          while (collides(position, entry.tool, placed) && attempts < 16) {
            if (layoutMode === "LR") position.y += side * 24;
            else position.x += side * 24;
            attempts += 1;
          }
          entry.tool.position(position);
          placed.push(entry.tool);
        });
      });
      const examplesByTool = new Map();
      cy.nodes("[type = 'example']").sort((a, b) => a.id().localeCompare(b.id())).forEach(example => {
        const tool = example.outgoers("edge[type = 'example_guidance']").targets().first();
        if (!tool || tool.empty()) return;
        if (!examplesByTool.has(tool.id())) examplesByTool.set(tool.id(), []);
        examplesByTool.get(tool.id()).push({ example, tool });
      });
      examplesByTool.forEach(group => {
        group.forEach((entry, index) => {
          const tp = entry.tool.position();
          const working = entry.tool.outgoers("edge[type = 'tool_support']").targets().first();
          const wp = working && !working.empty() ? working.position() : { x: tp.x, y: tp.y };
          const outward = layoutMode === "LR" ? (tp.y <= wp.y ? -1 : 1) : (tp.x <= wp.x ? -1 : 1);
          let position = layoutMode === "LR"
            ? { x: tp.x + (index - (group.length - 1) / 2) * 43, y: tp.y + outward * 61 }
            : { x: tp.x + outward * 68, y: tp.y + (index - (group.length - 1) / 2) * 43 };
          let attempts = 0;
          while (collides(position, entry.example, placed) && attempts < 16) {
            if (layoutMode === "LR") position.y += outward * 20;
            else position.x += outward * 20;
            attempts += 1;
          }
          entry.example.position(position);
          placed.push(entry.example);
        });
      });
    }

    function fitVisibleNodes() {
      const visibleNodes = cy.nodes(":visible");
      if (visibleNodes.empty()) return;
      cy.resize();
      cy.fit(visibleNodes, 48);
    }

    function seedRadialPositions(mainNodes) {
      const ordered = mainNodes.toArray().sort((a, b) => a.id().localeCompare(b.id(), undefined, { numeric: true }));
      const radius = Math.max(240, Math.sqrt(ordered.length) * 76);
      ordered.forEach((node, index) => {
        const angle = -Math.PI / 2 + index * Math.PI * 2 / Math.max(ordered.length, 1);
        node.position({ x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
      });
    }

    function collisionRadius(node) {
      if (node.data("type") === "working_state") return 31;
      if (node.data("type") === "skill_call") return 40;
      if (node.data("type") === "gate_collection") return 31;
      return 23;
    }

    function separateMainNodes(mainNodes, boundaryRadius) {
      const nodes = mainNodes.toArray().sort((a, b) => a.id().localeCompare(b.id(), undefined, { numeric: true }));
      for (let iteration = 0; iteration < 140; iteration += 1) {
        let moved = false;
        for (let left = 0; left < nodes.length; left += 1) {
          for (let right = left + 1; right < nodes.length; right += 1) {
            const a = nodes[left];
            const b = nodes[right];
            const ap = a.position();
            const bp = b.position();
            let dx = bp.x - ap.x;
            let dy = bp.y - ap.y;
            let distance = Math.hypot(dx, dy);
            const minimum = collisionRadius(a) + collisionRadius(b) + 10;
            if (distance >= minimum) continue;
            if (distance < 1e-6) {
              const angle = stableAngle(a.id() + "|" + b.id());
              dx = Math.cos(angle);
              dy = Math.sin(angle);
              distance = 1;
            }
            const push = (minimum - distance) * 0.52;
            const ux = dx / distance;
            const uy = dy / distance;
            a.position({ x: ap.x - ux * push, y: ap.y - uy * push });
            b.position({ x: bp.x + ux * push, y: bp.y + uy * push });
            moved = true;
          }
        }
        nodes.forEach(node => {
          const position = node.position();
          const distance = Math.hypot(position.x, position.y);
          if (distance > boundaryRadius) {
            const scale = boundaryRadius / distance;
            node.position({ x: position.x * scale, y: position.y * scale });
          }
        });
        if (!moved) break;
      }
    }

    function normalizeMainCircle(mainNodes) {
      const center = averagePosition(mainNodes);
      const targetRadius = Math.max(330, Math.sqrt(mainNodes.length) * 100);
      let maximum = 0;
      mainNodes.forEach(node => {
        const position = node.position();
        maximum = Math.max(maximum, Math.hypot(position.x - center.x, position.y - center.y));
      });
      const scale = maximum > 0 ? targetRadius / maximum : 1;
      mainNodes.forEach(node => {
        const position = node.position();
        node.position({ x: (position.x - center.x) * scale, y: (position.y - center.y) * scale });
      });
      separateMainNodes(mainNodes, targetRadius + 55);
      radialEnvelope = { center: { x: 0, y: 0 }, radius: targetRadius + 190 };
    }

    function confineToRadialEnvelope(nodes) {
      if (!radialEnvelope) return;
      nodes.forEach(node => {
        const position = node.position();
        const dx = position.x - radialEnvelope.center.x;
        const dy = position.y - radialEnvelope.center.y;
        const distance = Math.hypot(dx, dy);
        if (distance > radialEnvelope.radius) {
          const scale = radialEnvelope.radius / distance;
          node.position({
            x: radialEnvelope.center.x + dx * scale,
            y: radialEnvelope.center.y + dy * scale
          });
        }
      });
    }

    function runLayout(fit) {
      const mainNodes = cy.nodes().filter(node => MAIN_TYPES.has(node.data("type")));
      const mainEdges = cy.edges().filter(edge => MAIN_EDGES.has(edge.data("type")) && MAIN_TYPES.has(edge.source().data("type")) && MAIN_TYPES.has(edge.target().data("type")));
      const animateLayout = !reducedMotion && !selfTestMode;
      const canvas = document.getElementById("graph-canvas");
      canvas.classList.toggle("radial-mode", layoutMode === "RADIAL");
      if (layoutMode === "RADIAL") {
        seedRadialPositions(mainNodes);
        mainNodes.union(mainEdges).layout({
          name: "cose",
          animate: false,
          randomize: false,
          fit: false,
          nodeRepulsion: () => 7200,
          idealEdgeLength: () => 92,
          edgeElasticity: () => 160,
          nestingFactor: 1.2,
          gravity: 0.42,
          numIter: 900,
          initialTemp: 90,
          coolingFactor: 0.96,
          minTemp: 1
        }).run();
        normalizeMainCircle(mainNodes);
        placeSupportNodes();
        confineToRadialEnvelope(cy.nodes());
        if (fit) {
          fitVisibleNodes();
          window.setTimeout(fitVisibleNodes, 100);
        }
        return;
      }
      radialEnvelope = null;
      mainNodes.union(mainEdges).layout({
        name: "dagre", rankDir: layoutMode, nodeSep: 54, rankSep: 105, edgeSep: 28,
        animate: animateLayout, animationDuration: 280, fit: false, padding: 45
      }).run();
      const finalizeLayout = () => {
        placeSupportNodes();
        if (fit) {
          fitVisibleNodes();
          window.setTimeout(fitVisibleNodes, 100);
        }
      };
      if (animateLayout) window.setTimeout(finalizeLayout, 300);
      else finalizeLayout();
    }

    function clearClasses() {
      cy.elements().removeClass("dimmed focused edge-label");
      document.getElementById("condition-badge").classList.remove("visible");
    }

    function focusElement(element, showCondition) {
      clearClasses();
      if (!element || element.empty()) return;
      let neighborhood;
      if (element.isNode()) neighborhood = element.closedNeighborhood();
      else neighborhood = element.union(element.connectedNodes());
      cy.elements().not(neighborhood).addClass("dimmed");
      neighborhood.addClass("focused");
      if (element.isEdge() && showCondition && element.data("condition")) {
        element.addClass("edge-label");
        const badge = document.getElementById("condition-badge");
        badge.textContent = element.data("condition");
        badge.classList.add("visible");
      }
    }

    function section(container, title, values, options) {
      if (values === undefined || values === null || values === "") return;
      const block = make("section", null, "inspect-section");
      block.appendChild(make("h3", title));
      const list = Array.isArray(values) ? values : [values];
      if (list.length === 0) block.appendChild(make("p", "None stated", "muted"));
      else if (list.length === 1 && !(options && options.forceList)) block.appendChild(make("p", list[0]));
      else {
        const ul = make("ul");
        list.forEach(value => ul.appendChild(make("li", value)));
        block.appendChild(ul);
      }
      container.appendChild(block);
    }

    function sourceDescriptions(refs) {
      return (refs || []).map(ref => {
        let text = ref.file;
        if (ref.heading) text += " — " + ref.heading;
        if (ref.line_start) text += ":" + ref.line_start + (ref.line_end && ref.line_end !== ref.line_start ? "–" + ref.line_end : "");
        return text;
      });
    }

    function setCurrentIndex(id) {
      document.querySelectorAll("#node-index button").forEach(button => button.setAttribute("aria-current", button.dataset.nodeId === id ? "true" : "false"));
      const current = document.querySelector("#node-index button[aria-current='true']");
      if (current) current.scrollIntoView({ block: "nearest" });
    }

    function renderInspector(element, preview) {
      const title = document.getElementById("inspector-title");
      const content = document.getElementById("inspector-content");
      content.replaceChildren();
      if (!element || element.empty()) {
        title.textContent = "Select a node or edge";
        content.appendChild(make("p", "Hover for a preview, or click to pin complete details.", "muted"));
        setCurrentIndex("");
        return;
      }
      const isNode = element.isNode();
      const record = isNode ? nodesById.get(element.id()) : edgesById.get(element.id());
      title.textContent = element.id() + " — " + (record.title || record.summary || record.type);
      const status = make("span", record.extraction_status, "status-chip");
      content.appendChild(status);
      section(content, "Summary", record.summary || "No summary stated");
      if (preview) return;
      if (isNode) {
        if (record.type === "working_state") {
          section(content, "Detailed instructions", record.details);
          section(content, "Inputs", record.inputs, { forceList: true });
          section(content, "Outputs", record.outputs, { forceList: true });
          section(content, "Constraints", record.constraints, { forceList: true });
          section(content, "Terminal", record.terminal ? "Yes" : "No");
          section(content, "Incoming tools", element.incomers("edge[type = 'tool_support']").sources().map(node => node.id() + " — " + nodesById.get(node.id()).title), { forceList: true });
        } else if (record.type === "tool") {
          section(content, "Tool", record.tool_name + " (" + record.tool_category + ")");
          section(content, "Script or command", record.script_path || record.call_pattern || "Not stated");
          section(content, "Inputs", record.inputs, { forceList: true });
          section(content, "Outputs", record.outputs, { forceList: true });
          section(content, "Preconditions", record.preconditions, { forceList: true });
          const examples = element.incomers("edge[type = 'example_guidance']").sources();
          if (examples.length) {
            const block = make("section", null, "inspect-section");
            block.appendChild(make("h3", "Linked examples"));
            examples.forEach(example => {
              const button = make("button", example.id() + " — " + nodesById.get(example.id()).title, "outcome-button");
              button.addEventListener("click", () => pin(example));
              block.appendChild(button);
            });
            content.appendChild(block);
          }
        } else if (record.type === "example") {
          section(content, "Example", record.example_text);
          section(content, "Demonstrates", record.demonstrates);
          section(content, "Target tool", record.target_tool_id + " — " + (nodesById.get(record.target_tool_id) || {}).title);
        } else if (record.type === "gate_collection") {
          section(content, "Criteria", (record.criteria || []).map(item => (item.required ? "Required: " : "Optional: ") + item.text), { forceList: true });
          section(content, "Required evidence", record.required_evidence, { forceList: true });
          const block = make("section", null, "inspect-section");
          block.appendChild(make("h3", "Outcomes"));
          element.outgoers("edge").filter(edge => edge.data("type").startsWith("gate_") || edge.data("type") === "skill_invoke").forEach(edge => {
            const target = nodesById.get(edge.target().id());
            const text = edge.data("type") + ": " + (edge.data("condition") || "No condition") + " → " + edge.target().id() + " " + (target ? target.title : "");
            const button = make("button", text, "outcome-button");
            button.addEventListener("mouseenter", () => focusElement(edge, true));
            button.addEventListener("mouseleave", restorePinned);
            button.addEventListener("click", () => pin(edge));
            block.appendChild(button);
          });
          content.appendChild(block);
        } else if (record.type === "skill_call") {
          section(content, "Called skill", record.target_skill);
          section(content, "Skill path", record.target_skill_path);
          section(content, "Passed inputs", record.passed_inputs, { forceList: true });
          section(content, "Expected outputs", record.expected_outputs, { forceList: true });
          if (safeHref(record.target_xray_href)) {
            const link = make("a", "Open called skill graph", "called-skill-link");
            link.href = record.target_xray_href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            content.appendChild(link);
          }
        }
        const predecessors = element.incomers("edge").filter(edge => MAIN_EDGES.has(edge.data("type"))).sources();
        const successors = element.outgoers("edge").filter(edge => MAIN_EDGES.has(edge.data("type"))).targets();
        section(content, "Predecessors", predecessors.map(node => node.id() + " — " + nodesById.get(node.id()).title), { forceList: true });
        section(content, "Successors", successors.map(node => node.id() + " — " + nodesById.get(node.id()).title), { forceList: true });
      } else {
        section(content, "Source", record.source);
        section(content, "Target", record.target);
        section(content, "Edge type", record.type);
        section(content, "Condition", record.condition || "No condition stated");
      }
      section(content, "Source references", sourceDescriptions(record.source_refs), { forceList: true });
      if (isNode) setCurrentIndex(element.id());
    }

    function pin(element) {
      if (!element || element.empty()) return;
      pinnedId = element.id();
      focusElement(element, true);
      renderInspector(element, false);
    }

    function restorePinned() {
      if (pinnedId) {
        const element = cy.$id(pinnedId);
        if (!element.empty()) {
          focusElement(element, true);
          renderInspector(element, false);
          return;
        }
      }
      clearClasses();
      renderInspector(null, false);
    }

    cy.on("mouseover", "node, edge", event => {
      const element = event.target;
      focusElement(element, element.isEdge());
      renderInspector(element, true);
    });
    cy.on("mouseout", "node, edge", restorePinned);
    cy.on("tap", "node, edge", event => pin(event.target));
    cy.on("tap", event => {
      if (event.target === cy) {
        pinnedId = null;
        restorePinned();
      }
    });

    function buildIndex() {
      const index = document.getElementById("node-index");
      index.replaceChildren();
      Object.keys(TYPE_META).forEach(type => {
        const matching = graph.nodes.filter(node => node.type === type).sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
        if (!matching.length) return;
        const group = make("div", null, "index-group");
        group.appendChild(make("h3", TYPE_META[type].label + " (" + matching.length + ")"));
        matching.forEach(node => {
          const button = make("button", node.id + " — " + node.title);
          button.type = "button";
          button.dataset.nodeId = node.id;
          button.setAttribute("aria-label", TYPE_META[type].label + ": " + node.title);
          button.addEventListener("click", () => {
            const element = cy.$id(node.id);
            cy.animate({ center: { eles: element }, zoom: Math.max(cy.zoom(), .8), duration: reducedMotion ? 0 : 220 });
            pin(element);
          });
          group.appendChild(button);
        });
        index.appendChild(group);
      });
    }

    function buildLegend() {
      const legend = document.getElementById("legend");
      legend.replaceChildren();
      const classes = { working_state: "working", tool: "tool", example: "example", gate_collection: "gate", skill_call: "skill" };
      Object.keys(TYPE_META).forEach(type => {
        const row = make("div", null, "legend-row");
        const shape = make("span", null, "legend-shape " + classes[type]);
        shape.appendChild(make("span", TYPE_META[type].prefix));
        row.appendChild(shape);
        row.appendChild(make("span", TYPE_META[type].label));
        legend.appendChild(row);
        if (type === "working_state") {
          const terminalRow = make("div", null, "legend-row");
          const terminalShape = make("span", null, "legend-shape terminal-working");
          terminalShape.appendChild(make("span", TYPE_META[type].prefix));
          terminalRow.appendChild(terminalShape);
          terminalRow.appendChild(make("span", "Terminal working states"));
          legend.appendChild(terminalRow);
        }
      });
    }

    function updateFilters() {
      const enabled = new Set(Array.from(document.querySelectorAll("#node-filters input:checked")).map(input => input.value));
      cy.nodes().forEach(node => node.toggleClass("filtered", !enabled.has(node.data("type"))));
      cy.edges().forEach(edge => edge.toggleClass("filtered", edge.source().hasClass("filtered") || edge.target().hasClass("filtered")));
    }

    function buildFilters() {
      const container = document.getElementById("node-filters");
      container.replaceChildren();
      Object.keys(TYPE_META).forEach(type => {
        const label = make("label");
        const input = make("input");
        input.type = "checkbox";
        input.value = type;
        input.checked = true;
        input.addEventListener("change", updateFilters);
        label.appendChild(input);
        label.appendChild(make("span", TYPE_META[type].label));
        container.appendChild(label);
      });
    }

    function searchable(node) {
      const refs = (node.source_refs || []).map(ref => ref.file).join(" ");
      const criteria = (node.criteria || []).map(item => item.text).join(" ");
      return [node.id, node.title, node.summary, node.tool_name, node.target_skill, refs, criteria].filter(Boolean).join(" ").toLowerCase();
    }

    function runSearch(queryOverride) {
      const input = document.getElementById("search-input");
      const query = (queryOverride !== undefined ? queryOverride : input.value).trim().toLowerCase();
      const results = document.getElementById("search-results");
      results.replaceChildren();
      if (!query) return [];
      const matches = graph.nodes.filter(node => searchable(node).includes(query)).slice(0, 40);
      matches.forEach(node => {
        const button = make("button", node.id + " — " + node.title);
        button.type = "button";
        button.setAttribute("role", "option");
        button.addEventListener("click", () => pin(cy.$id(node.id)));
        results.appendChild(button);
      });
      return matches;
    }

    document.getElementById("search-input").addEventListener("input", () => runSearch());
    document.getElementById("fit-button").addEventListener("click", fitVisibleNodes);
    document.getElementById("reset-button").addEventListener("click", () => { pinnedId = null; restorePinned(); fitVisibleNodes(); });
    document.getElementById("direction-button").addEventListener("click", event => {
      const current = LAYOUT_MODES.indexOf(layoutMode);
      layoutMode = LAYOUT_MODES[(current + 1) % LAYOUT_MODES.length];
      event.currentTarget.textContent = "Layout: " + layoutMode;
      runLayout(true);
    });
    document.getElementById("theme-button").addEventListener("click", event => {
      document.body.classList.toggle("dark");
      event.currentTarget.textContent = document.body.classList.contains("dark") ? "Light theme" : "Dark theme";
    });
    document.getElementById("toggle-left").addEventListener("click", () => document.getElementById("left-sidebar").classList.toggle("open"));
    document.getElementById("toggle-right").addEventListener("click", () => document.getElementById("right-sidebar").classList.toggle("open"));

    buildLegend();
    buildFilters();
    buildIndex();
    renderInspector(null, false);
    document.getElementById("direction-button").textContent = "Layout: " + layoutMode;
    runLayout(true);

    function runSelfTests() {
      const checks = [];
      const check = (name, passed, detail) => checks.push({ name, passed: Boolean(passed), detail: detail || "" });
      check("graph_loaded", cy.nodes().length === graph.nodes.length && cy.edges().length === graph.edges.length, cy.nodes().length + " nodes");
      check("compact_canvas_labels", cy.nodes().every(node => node.data("label") === node.id()));
      const tool = cy.nodes("[type = 'tool']").first();
      const skill = cy.nodes("[type = 'skill_call']").first();
      const working = cy.nodes("[type = 'working_state']").first();
      const terminalWorking = cy.nodes("[type = 'working_state'][?terminal]").first();
      if (!tool.empty()) check("tool_fixed_size", parseFloat(tool.style("width")) === 26, tool.style("width"));
      if (!tool.empty() && !skill.empty()) check("tool_smaller_than_skill", parseFloat(tool.style("width")) < parseFloat(skill.style("width")));
      if (!working.empty()) check("working_state_circle", working.style("shape") === "ellipse" && parseFloat(working.style("width")) === parseFloat(working.style("height")), working.style("shape") + " " + working.style("width") + " x " + working.style("height"));
      if (!terminalWorking.empty()) check("terminal_working_color_distinct", terminalWorking.style("background-color") !== colors.working && parseFloat(terminalWorking.style("border-width")) === 4, terminalWorking.style("background-color") + " / " + terminalWorking.style("border-width"));
      const first = cy.nodes().first();
      pin(first);
      check("click_pin_state", pinnedId === first.id());
      const searchMatches = runSearch((nodesById.get(first.id()).title || first.id()).slice(0, 4));
      check("search", searchMatches.some(node => node.id === first.id()), searchMatches.length + " matches");
      const gate = cy.nodes("[type = 'gate_collection']").first();
      if (!working.empty() && !gate.empty()) check("working_state_gate_size_match", parseFloat(working.style("width")) === parseFloat(gate.style("width")) && parseFloat(working.style("height")) === parseFloat(gate.style("height")), working.style("width") + " x " + working.style("height") + " / gate " + gate.style("width") + " x " + gate.style("height"));
      if (!gate.empty()) check("gate_outcomes", gate.outgoers("edge").filter(edge => edge.data("type").startsWith("gate_") || edge.data("type") === "skill_invoke").length >= 1);
      check("unsafe_link_rejected", !safeHref("javascript:alert(1)"));
      check("relative_link_allowed", safeHref("../called/graph.html"));
      const csp = document.querySelector("meta[http-equiv='Content-Security-Policy']");
      check("no_network_csp", csp && csp.content.includes("connect-src 'none'"));
      check("radial_layout_available", LAYOUT_MODES.includes("RADIAL"));
      check("complex_graph_defaults_radial", mainNodeCount < 15 || layoutMode === "RADIAL", layoutMode);
      if (layoutMode === "RADIAL" && radialEnvelope) {
        const maximumRadius = cy.nodes().reduce((maximum, node) => {
          const position = node.position();
          return Math.max(maximum, Math.hypot(position.x - radialEnvelope.center.x, position.y - radialEnvelope.center.y));
        }, 0);
        check("radial_envelope", maximumRadius <= radialEnvelope.radius + 1e-6, maximumRadius.toFixed(3) + " / " + radialEnvelope.radius.toFixed(3));
        const mainNodes = cy.nodes().filter(node => MAIN_TYPES.has(node.data("type")));
        const mainEdges = cy.edges().filter(edge => MAIN_EDGES.has(edge.data("type")) && MAIN_TYPES.has(edge.source().data("type")) && MAIN_TYPES.has(edge.target().data("type")));
        const edgeLengths = mainEdges.map(edge => {
          const source = edge.source().position();
          const target = edge.target().position();
          return Math.hypot(source.x - target.x, source.y - target.y);
        });
        const pairLengths = [];
        const mainArray = mainNodes.toArray();
        for (let left = 0; left < mainArray.length; left += 1) {
          for (let right = left + 1; right < mainArray.length; right += 1) {
            const a = mainArray[left].position();
            const b = mainArray[right].position();
            pairLengths.push(Math.hypot(a.x - b.x, a.y - b.y));
          }
        }
        const mean = values => values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
        const edgeMean = mean(edgeLengths);
        const pairMean = mean(pairLengths);
        check("connected_nodes_cluster", edgeMean < pairMean, edgeMean.toFixed(3) + " < " + pairMean.toFixed(3));
        let minimumClearance = Infinity;
        for (let left = 0; left < mainArray.length; left += 1) {
          for (let right = left + 1; right < mainArray.length; right += 1) {
            const a = mainArray[left];
            const b = mainArray[right];
            const ap = a.position();
            const bp = b.position();
            const clearance = Math.hypot(ap.x - bp.x, ap.y - bp.y) - collisionRadius(a) - collisionRadius(b);
            minimumClearance = Math.min(minimumClearance, clearance);
          }
        }
        check("radial_main_node_clearance", minimumClearance >= 9.5, minimumClearance.toFixed(3));
        const visibleArray = cy.nodes(":visible").toArray();
        let minimumSymbolClearance = Infinity;
        for (let left = 0; left < visibleArray.length; left += 1) {
          for (let right = left + 1; right < visibleArray.length; right += 1) {
            const a = visibleArray[left];
            const b = visibleArray[right];
            const ap = a.position();
            const bp = b.position();
            const clearance = Math.hypot(ap.x - bp.x, ap.y - bp.y) - collisionRadius(a) - collisionRadius(b);
            minimumSymbolClearance = Math.min(minimumSymbolClearance, clearance);
          }
        }
        check("radial_all_symbol_clearance", minimumSymbolClearance >= 7.5, minimumSymbolClearance.toFixed(3));
      }
      fitVisibleNodes();
      const rendered = cy.nodes(":visible").renderedBoundingBox({ includeLabels: true, includeOverlays: false });
      check(
        "visible_nodes_inside_viewport",
        rendered.x1 >= -1 && rendered.y1 >= -1 && rendered.x2 <= cy.width() + 1 && rendered.y2 <= cy.height() + 1,
        JSON.stringify({ x1: rendered.x1, y1: rendered.y1, x2: rendered.x2, y2: rendered.y2, width: cy.width(), height: cy.height() })
      );
      pinnedId = null;
      restorePinned();
      const result = { passed: checks.every(item => item.passed), checks: checks };
      const output = document.getElementById("xray-selftest");
      output.textContent = JSON.stringify(result);
      output.dataset.status = result.passed ? "pass" : "fail";
      return result;
    }

    window.skillXrayApp = { cy, graph, pin, runSearch, runLayout, runSelfTests, safeHref, fitVisibleNodes, getLayoutMode: () => layoutMode };
    document.getElementById("xray-app").dataset.xrayReady = "true";
    if (selfTestMode) {
      window.setTimeout(runSelfTests, 50);
    }
  }

  try {
    boot();
  } catch (error) {
    const output = document.getElementById("xray-selftest");
    output.textContent = JSON.stringify({ passed: false, fatal: String(error && error.stack || error) });
    output.dataset.status = "fail";
    document.getElementById("xray-app").dataset.xrayReady = "error";
    throw error;
  }
}());
