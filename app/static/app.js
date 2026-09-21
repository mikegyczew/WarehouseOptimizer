class WarehouseApp {
    constructor() {
        this.packageId = 0;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.animatedBoxes = [];
        this.animationLoopStarted = false;
        this.cameraTarget = null;
        this.cameraDistance = 5;
        this.cameraAngleX = 0.8;
        this.cameraAngleY = 0.7;
        this.roomGroup = null;
        this.grid = null;
        this.warehouseObjects = [];
        this.mouseDown = false;
        this.isDragging = false;
        this.pointerMoved = false;
        this.previousMouseX = 0;
        this.previousMouseY = 0;
        this.gridVisible = true;
        this.currentResult = null;
        this.selectedMesh = null;
        this.selectedBox = null;
        this.raycaster = null;
        this.mouse = null;

        this.bindGlobalHandlers();
        this.bindWindowEvents();
        window.addEventListener("load", () => {
            this.showView("dashboard");
            this.updateInventory();
            this.updateRoomSidebar();
            this.bindFileInput();
            this.loadDemo();
        });
    }

    bindFileInput() {
        const input = document.getElementById("excelFileInput");
        if (!input) return;

        input.addEventListener("change", (event) => {
            const file = event.target.files && event.target.files[0];
            if (file) {
                this.importExcelData(file);
            }
            event.target.value = "";
        });
    }

    bindGlobalHandlers() {
        Object.assign(window, {
            showView: (name) => this.showView(name),
            saveRoom: () => this.saveRoom(),
            updateRoomSidebar: () => this.updateRoomSidebar(),
            addPackage: () => this.addPackage(),
            removePackage: (button) => this.removePackage(button),
            updatePackageNumbers: () => this.updatePackageNumbers(),
            updateInventory: () => this.updateInventory(),
            updateDashboard: () => this.updateDashboard(),
            optimize: () => this.optimize(),
            applyResult: (result) => this.applyResult(result),
            updateUsageCircle: (value) => this.updateUsageCircle(value),
            getBoxVolume: (box) => this.getBoxVolume(box),
            getVolumeColor: (volume, minVolume, maxVolume, T) => this.getVolumeColor(volume, minVolume, maxVolume, T),
            create3DLegend: (container) => this.create3DLegend(container),
            renderWarehouse: (roomData, boxes) => this.renderWarehouse(roomData, boxes),
            updateAnimationProgress: () => this.updateAnimationProgress(),
            fitCamera: () => this.fitCamera(),
            resetCamera: () => this.resetCamera(),
            updateCamera: () => this.updateCamera(),
            animate3D: () => this.animate3D(),
            onScenePointerDown: (event) => this.onScenePointerDown(event),
            onScenePointerMove: (event) => this.onScenePointerMove(event),
            onScenePointerUp: (event) => this.onScenePointerUp(event),
            onScenePointerLeave: () => this.onScenePointerLeave(),
            onSceneWheel: (event) => this.onSceneWheel(event),
            onSceneClick: (event) => this.onSceneClick(event),
            selectBox: (mesh) => this.selectBox(mesh),
            formatNumber: (value) => this.formatNumber(value),
            resetBoxMaterial: () => this.resetBoxMaterial(),
            clearSelectedBox: () => this.clearSelectedBox(),
            toggleGrid: () => this.toggleGrid(),
            resize3D: () => this.resize3D(),
            loadDemo: () => this.loadDemo(),
            downloadExcelTemplate: () => this.downloadExcelTemplate(),
            importExcelData: (file) => this.importExcelData(file),
        });
    }

    bindWindowEvents() {
        window.addEventListener("resize", () => this.resize3D());
    }

    showView(name) {
        document.querySelectorAll(".view").forEach((view) => view.classList.add("hidden"));

        const target = document.getElementById(`${name}View`);
        if (target) {
            target.classList.remove("hidden");
        }

        document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));

        const navItems = document.querySelectorAll(".nav-item");
        const index = { dashboard: 0, warehouse: 1, packages: 2, settings: 3 }[name];

        if (navItems[index]) {
            navItems[index].classList.add("active");
        }
    }

    saveRoom() {
        const length = Number(document.getElementById("roomLength").value);
        const width = Number(document.getElementById("roomWidth").value);
        const height = Number(document.getElementById("roomHeight").value);

        if (length <= 0 || width <= 0 || height <= 0) {
            alert("Podaj poprawne wymiary magazynu.");
            return;
        }

        const volume = (length * width * height) / 1000000;
        const base = (length * width) / 10000;

        document.getElementById("roomVolume").textContent = `${volume.toFixed(2)} m³`;
        document.getElementById("roomBase").textContent = `${base.toFixed(2)} m²`;

        this.updateRoomSidebar();
        this.updateDashboard();
        this.showView("packages");

        if (document.querySelectorAll(".package-row").length === 0) {
            this.addPackage();
        }
    }

    updateRoomSidebar() {
        const length = document.getElementById("roomLength").value;
        const width = document.getElementById("roomWidth").value;
        const height = document.getElementById("roomHeight").value;

        document.getElementById("sideLength").textContent = length ? `${length} cm` : "—";
        document.getElementById("sideWidth").textContent = width ? `${width} cm` : "—";
        document.getElementById("sideHeight").textContent = height ? `${height} cm` : "—";
    }

    addPackage() {
        this.packageId += 1;

        const row = document.createElement("div");
        row.className = "package-row";
        row.innerHTML = `
            <div class="package-index">${this.packageId}</div>
            <div class="field">
                <label>Nazwa</label>
                <input class="name" type="text" placeholder="Karton A" oninput="updateInventory()">
            </div>
            <div class="field">
                <label>Długość</label>
                <div class="unit-input">
                    <input class="length" type="number" placeholder="80" min="1" oninput="updateInventory()">
                    <span>cm</span>
                </div>
            </div>
            <div class="field">
                <label>Szerokość</label>
                <div class="unit-input">
                    <input class="width" type="number" placeholder="40" min="1" oninput="updateInventory()">
                    <span>cm</span>
                </div>
            </div>
            <div class="field">
                <label>Wysokość</label>
                <div class="unit-input">
                    <input class="height" type="number" placeholder="30" min="1" oninput="updateInventory()">
                    <span>cm</span>
                </div>
            </div>
            <div class="field">
                <label>Ilość</label>
                <input class="quantity" type="number" value="1" min="1" oninput="updateInventory()">
            </div>
            <button class="remove-button" onclick="removePackage(this)">×</button>
        `;

        document.getElementById("packagesList").appendChild(row);
        this.updateInventory();
    }

    removePackage(button) {
        button.closest(".package-row").remove();
        this.updatePackageNumbers();
        this.updateInventory();
    }

    updatePackageNumbers() {
        document.querySelectorAll(".package-row").forEach((row, index) => {
            row.querySelector(".package-index").textContent = index + 1;
        });
    }

    updateInventory() {
        const rows = document.querySelectorAll(".package-row");
        let count = 0;
        let volume = 0;

        rows.forEach((row) => {
            const length = Number(row.querySelector(".length").value);
            const width = Number(row.querySelector(".width").value);
            const height = Number(row.querySelector(".height").value);
            const quantity = Number(row.querySelector(".quantity").value) || 0;

            count += quantity;

            if (length > 0 && width > 0 && height > 0) {
                volume += ((length * width * height * quantity) / 1000000);
            }
        });

        document.getElementById("packageTypes").textContent = rows.length;
        document.getElementById("packageCount").textContent = count;
        document.getElementById("packageVolume").textContent = `${volume.toFixed(2)} m³`;
        document.getElementById("dashboardPackages").textContent = count;
        document.getElementById("emptyPackages").classList.toggle("hidden", rows.length > 0);
        this.updateDashboard();
    }

    updateDashboard() {
        const length = Number(document.getElementById("roomLength").value) || 0;
        const width = Number(document.getElementById("roomWidth").value) || 0;
        const height = Number(document.getElementById("roomHeight").value) || 0;
        const volume = (length * width * height) / 1000000;

        document.getElementById("dashboardRoom").textContent = volume ? `${volume.toFixed(2)} m³` : "0 m³";
    }

    async optimize() {
        const roomLength = Number(document.getElementById("roomLength").value);
        const roomWidth = Number(document.getElementById("roomWidth").value);
        const roomHeight = Number(document.getElementById("roomHeight").value);

        if (roomLength <= 0 || roomWidth <= 0 || roomHeight <= 0) {
            alert("Najpierw ustaw poprawne wymiary magazynu.");
            this.showView("warehouse");
            return;
        }

        const rows = document.querySelectorAll(".package-row");
        const packages = [];

        rows.forEach((row) => {
            const name = row.querySelector(".name").value.trim();
            const length = Number(row.querySelector(".length").value);
            const width = Number(row.querySelector(".width").value);
            const height = Number(row.querySelector(".height").value);
            const quantity = Number(row.querySelector(".quantity").value);

            if (name && length > 0 && width > 0 && height > 0 && quantity > 0) {
                packages.push({ name, length, width, height, quantity });
            }
        });

        if (packages.length === 0) {
            alert("Dodaj przynajmniej jeden poprawnie wypełniony towar.");
            this.showView("packages");
            return;
        }

        const loading = document.getElementById("loading");
        loading.classList.remove("hidden");

        try {
            const response = await fetch("/api/optimize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    room_length: roomLength,
                    room_width: roomWidth,
                    room_height: roomHeight,
                    packages,
                }),
            });

            if (!response.ok) {
                throw new Error(await response.text());
            }

            const result = await response.json();
            this.currentResult = result;
            this.applyResult(result);
            this.showView("dashboard");
        } catch (error) {
            console.error(error);
            alert(`Błąd optymalizacji:\n\n${error.message}`);
        } finally {
            loading.classList.add("hidden");
        }
    }

    applyResult(result) {
        const placed = result.optimization.placed;
        const notPlaced = result.optimization.not_placed;
        const usage = result.optimization.utilization;

        document.getElementById("dashboardPlaced").textContent = placed;
        document.getElementById("dashboardUsage").textContent = `${usage}%`;
        document.getElementById("miniPlaced").textContent = placed;
        document.getElementById("miniNotPlaced").textContent = notPlaced;
        document.getElementById("circleUsage").textContent = `${usage}%`;

        this.updateUsageCircle(usage);

        if (window.THREE) {
            this.renderWarehouse(result.room, result.placed_boxes);
        } else {
            console.warn("Three.js niedostępny.");
        }
    }

    updateUsageCircle(value) {
        const circle = document.querySelector(".usage-circle");
        if (!circle) return;

        const safe = Math.max(0, Math.min(100, Number(value) || 0));
        circle.style.setProperty("--usage", `${safe}%`);
    }

    getBoxVolume(box) {
        return Number(box.length) * Number(box.width) * Number(box.height);
    }

    getVolumeColor(volume, minVolume, maxVolume, T) {
        let normalized = 0.5;

        if (maxVolume > minVolume) {
            normalized = (volume - minVolume) / (maxVolume - minVolume);
        }

        normalized = Math.max(0, Math.min(1, normalized));
        const hue = 0.62 - normalized * 0.62;
        const color = new T.Color();
        color.setHSL(hue, 0.72, 0.52);
        return color;
    }

    create3DLegend(container) {
        const existing = document.getElementById("warehouse3dLegend");
        if (existing) existing.remove();

        const legend = document.createElement("div");
        legend.id = "warehouse3dLegend";
        legend.innerHTML = `
            <div class="warehouse-legend-title">ROZMIAR PACZKI</div>
            <div class="warehouse-legend-row"><span class="warehouse-legend-color" style="background:#2677ff;"></span>Małe</div>
            <div class="warehouse-legend-row"><span class="warehouse-legend-color" style="background:#34b85a;"></span>Małe / średnie</div>
            <div class="warehouse-legend-row"><span class="warehouse-legend-color" style="background:#e6c52f;"></span>Średnie</div>
            <div class="warehouse-legend-row"><span class="warehouse-legend-color" style="background:#ed8a24;"></span>Duże</div>
            <div class="warehouse-legend-row"><span class="warehouse-legend-color" style="background:#e53935;"></span>Największe</div>
        `;
        container.appendChild(legend);
    }

    renderWarehouse(roomData, boxes) {
        const T = window.THREE;
        if (!T) {
            console.error("Three.js nie jest jeszcze załadowany.");
            return;
        }

        const container = document.getElementById("scene");
        if (!container) return;

        if (this.renderer) {
            this.renderer.dispose();
            this.renderer = null;
        }

        const oldCanvas = container.querySelector("canvas");
        if (oldCanvas) oldCanvas.remove();

        const oldInfo = document.getElementById("warehouse3dInfo");
        if (oldInfo) oldInfo.remove();

        this.warehouseObjects = [];
        this.animatedBoxes = [];
        this.selectedMesh = null;
        this.selectedBox = null;

        this.raycaster = new T.Raycaster();
        this.mouse = new T.Vector2();

        this.scene = new T.Scene();
        this.scene.background = new T.Color(0x050b14);

        this.camera = new T.PerspectiveCamera(
            45,
            container.clientWidth / Math.max(container.clientHeight, 1),
            0.01,
            1000
        );

        this.renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = T.PCFSoftShadowMap;

        if ("outputColorSpace" in this.renderer) {
            this.renderer.outputColorSpace = T.SRGBColorSpace;
        }

        if ("toneMapping" in this.renderer) {
            this.renderer.toneMapping = T.ACESFilmicToneMapping;
            this.renderer.toneMappingExposure = 1.1;
        }

        container.appendChild(this.renderer.domElement);

        this.renderer.domElement.addEventListener("pointerdown", (event) => this.onScenePointerDown(event));
        this.renderer.domElement.addEventListener("pointermove", (event) => this.onScenePointerMove(event));
        this.renderer.domElement.addEventListener("pointerup", (event) => this.onScenePointerUp(event));
        this.renderer.domElement.addEventListener("pointerleave", () => this.onScenePointerLeave());
        this.renderer.domElement.addEventListener("wheel", (event) => this.onSceneWheel(event), { passive: true });

        const hemisphere = new T.HemisphereLight(0xbfd7ff, 0x101722, 2.2);
        this.scene.add(hemisphere);

        const mainLight = new T.DirectionalLight(0xffffff, 3.5);
        mainLight.position.set(8, 12, 6);
        mainLight.castShadow = true;
        mainLight.shadow.mapSize.width = 2048;
        mainLight.shadow.mapSize.height = 2048;
        mainLight.shadow.camera.near = 0.1;
        mainLight.shadow.camera.far = 50;
        mainLight.shadow.camera.left = -20;
        mainLight.shadow.camera.right = 20;
        mainLight.shadow.camera.top = 20;
        mainLight.shadow.camera.bottom = -20;
        this.scene.add(mainLight);

        const fillLight = new T.DirectionalLight(0x5b8cff, 1.2);
        fillLight.position.set(-8, 7, -5);
        this.scene.add(fillLight);

        const scale = 0.01;
        const roomL = roomData.length * scale;
        const roomW = roomData.width * scale;
        const roomH = roomData.height * scale;

        const floor = new T.Mesh(
            new T.BoxGeometry(roomL, 0.08, roomW),
            new T.MeshStandardMaterial({ color: 0x182332, roughness: 0.75, metalness: 0.15 })
        );
        floor.position.set(roomL / 2, -0.04, roomW / 2);
        floor.receiveShadow = true;
        this.scene.add(floor);

        this.roomGroup = new T.Group();
        this.scene.add(this.roomGroup);

        this.grid = new T.GridHelper(Math.max(roomL, roomW), 20, 0x3b82f6, 0x243247);
        this.grid.position.set(roomL / 2, 0.005, roomW / 2);
        this.gridVisible = true;
        this.grid.visible = true;
        this.roomGroup.add(this.grid);

        const roomGeometry = new T.BoxGeometry(roomL, roomH, roomW);
        const roomEdges = new T.EdgesGeometry(roomGeometry);
        const roomLines = new T.LineSegments(
            roomEdges,
            new T.LineBasicMaterial({ color: 0x4f8cff, transparent: true, opacity: 0.65 })
        );
        roomLines.position.set(roomL / 2, roomH / 2, roomW / 2);
        this.roomGroup.add(roomLines);

        const postMaterial = new T.MeshStandardMaterial({ color: 0x26364a, metalness: 0.6, roughness: 0.35 });
        const postRadius = 0.035;
        const postPositions = [[0, 0], [roomL, 0], [0, roomW], [roomL, roomW]];

        postPositions.forEach(([x, z]) => {
            const post = new T.Mesh(
                new T.CylinderGeometry(postRadius, postRadius, roomH, 12),
                postMaterial
            );
            post.position.set(x, roomH / 2, z);
            post.castShadow = true;
            this.roomGroup.add(post);
        });

        const sortedBoxes = [...boxes].sort((a, b) => this.getBoxVolume(b) - this.getBoxVolume(a));
        const volumes = sortedBoxes.map((box) => this.getBoxVolume(box));
        const minVolume = volumes.length ? Math.min(...volumes) : 0;
        const maxVolume = volumes.length ? Math.max(...volumes) : 0;

        this.create3DLegend(container);

        sortedBoxes.forEach((box, index) => {
            const width = Number(box.length) * scale;
            const height = Number(box.height) * scale;
            const depth = Number(box.width) * scale;
            const volume = this.getBoxVolume(box);
            const color = this.getVolumeColor(volume, minVolume, maxVolume, T);

            const mesh = new T.Mesh(
                new T.BoxGeometry(width, height, depth),
                new T.MeshStandardMaterial({
                    color,
                    roughness: 0.55,
                    metalness: 0.05,
                    emissive: new T.Color(0x000000),
                    emissiveIntensity: 0,
                })
            );

            const targetX = (Number(box.x) + Number(box.length) / 2) * scale;
            const targetY = (Number(box.z) + Number(box.height) / 2) * scale;
            const targetZ = (Number(box.y) + Number(box.width) / 2) * scale;
            const startY = roomH + 0.8 + index * 0.04;

            mesh.position.set(targetX, startY, targetZ);
            mesh.scale.set(0.75, 0.75, 0.75);
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            const edge = new T.LineSegments(
                new T.EdgesGeometry(new T.BoxGeometry(width, height, depth)),
                new T.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 })
            );
            mesh.add(edge);

            mesh.userData = {
                name: box.name,
                length: Number(box.length),
                width: Number(box.width),
                height: Number(box.height),
                x: Number(box.x),
                y: Number(box.y),
                z: Number(box.z),
                volume,
                originalColor: color.clone(),
                originalEmissive: 0,
            };

            this.scene.add(mesh);
            this.warehouseObjects.push(mesh);

            this.animatedBoxes.push({
                mesh,
                start: { x: targetX, y: startY, z: targetZ },
                target: { x: targetX, y: targetY, z: targetZ },
                startTime: performance.now() + index * 80,
                duration: 500,
                finished: false,
            });
        });

        const info = document.createElement("div");
        info.id = "warehouse3dInfo";
        info.innerHTML = `<strong>Optymalizacja 3D</strong><span>${sortedBoxes.length} paczek</span>`;
        Object.assign(info.style, {
            position: "absolute",
            left: "20px",
            bottom: "20px",
            padding: "10px 14px",
            borderRadius: "10px",
            background: "rgba(5, 11, 20, 0.85)",
            border: "1px solid rgba(100,150,255,.25)",
            color: "#dbeafe",
            fontSize: "13px",
            pointerEvents: "none",
            backdropFilter: "blur(8px)",
        });
        container.appendChild(info);

        this.cameraTarget = new T.Vector3(roomL / 2, roomH * 0.35, roomW / 2);
        const diagonal = Math.sqrt(roomL * roomL + roomW * roomW + roomH * roomH);
        this.cameraDistance = Math.max(diagonal * 1.35, 3);
        this.cameraAngleX = 0.8;
        this.cameraAngleY = 0.65;
        this.updateCamera();

        const progress = document.getElementById("warehouseProgress");
        const progressLabel = document.getElementById("warehouseProgressLabel");
        const progressTitle = document.getElementById("warehouseProgressTitle");
        if (progress) progress.style.width = "0%";
        if (progressLabel) progressLabel.textContent = `0 / ${this.animatedBoxes.length} · 0%`;
        if (progressTitle) progressTitle.textContent = this.animatedBoxes.length > 0 ? "Rozmieszczanie paczek" : "Brak paczek";

        const animationInfo = document.getElementById("warehouseAnimationInfo");
        if (animationInfo) {
            animationInfo.style.display = this.animatedBoxes.length > 0 ? "block" : "none";
        }

        if (!this.animationLoopStarted) {
            this.animationLoopStarted = true;
            this.animate3D();
        }
    }

    updateAnimationProgress() {
        const progress = document.getElementById("warehouseProgress");
        const label = document.getElementById("warehouseProgressLabel");
        const title = document.getElementById("warehouseProgressTitle");
        if (!progress || !label || !title) return;

        const total = this.animatedBoxes.length;
        if (total === 0) {
            progress.style.width = "100%";
            label.textContent = "0 / 0 · 100%";
            title.textContent = "Brak paczek";
            return;
        }

        const now = performance.now();
        let totalProgress = 0;
        let completed = 0;

        this.animatedBoxes.forEach((item) => {
            let itemProgress;
            if (item.finished) itemProgress = 1;
            else if (now < item.startTime) itemProgress = 0;
            else {
                itemProgress = (now - item.startTime) / item.duration;
                itemProgress = Math.max(0, Math.min(1, itemProgress));
            }

            totalProgress += itemProgress;
            if (itemProgress >= 1) completed++;
        });

        let percentage = (totalProgress / total) * 100;
        percentage = Math.max(0, Math.min(100, percentage));
        if (completed === total) percentage = 100;

        progress.style.width = `${percentage.toFixed(1)}%`;
        label.textContent = `${completed} / ${total} · ${Math.round(percentage)}%`;
        title.textContent = completed === total ? "Rozmieszczenie zakończone" : "Rozmieszczanie paczek";
    }

    fitCamera() {
        if (!this.camera || !this.currentResult || !this.cameraTarget) return;

        const room = this.currentResult.room;
        const scale = 0.01;
        const roomL = room.length * scale;
        const roomW = room.width * scale;
        const roomH = room.height * scale;

        this.cameraTarget.set(roomL / 2, roomH * 0.35, roomW / 2);
        this.cameraAngleX = 0.8;
        this.cameraAngleY = 0.65;

        const diagonal = Math.sqrt(roomL * roomL + roomW * roomW + roomH * roomH);
        this.cameraDistance = Math.max(diagonal * 1.35, 3);
        this.updateCamera();
    }

    resetCamera() {
        this.fitCamera();
    }

    updateCamera() {
        if (!this.camera || !this.cameraTarget) return;

        const horizontal = Math.cos(this.cameraAngleY) * this.cameraDistance;
        const x = this.cameraTarget.x + Math.sin(this.cameraAngleX) * horizontal;
        const y = this.cameraTarget.y + Math.sin(this.cameraAngleY) * this.cameraDistance;
        const z = this.cameraTarget.z + Math.cos(this.cameraAngleX) * horizontal;

        this.camera.position.set(x, y, z);
        this.camera.lookAt(this.cameraTarget);
    }

    animate3D() {
        requestAnimationFrame(() => this.animate3D());

        if (!this.renderer || !this.scene || !this.camera) return;

        const now = performance.now();

        this.animatedBoxes.forEach((item) => {
            if (item.finished) return;
            if (now < item.startTime) return;

            const elapsed = now - item.startTime;
            const progress = Math.min(elapsed / item.duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);

            item.mesh.position.x = item.start.x + (item.target.x - item.start.x) * eased;
            item.mesh.position.z = item.start.z + (item.target.z - item.start.z) * eased;

            const bounce = Math.sin(progress * Math.PI) * 0.12;
            item.mesh.position.y = item.start.y + (item.target.y - item.start.y) * eased + bounce;

            const scale = 0.75 + 0.25 * eased;
            item.mesh.scale.set(scale, scale, scale);

            if (progress >= 1) {
                item.mesh.position.set(item.target.x, item.target.y, item.target.z);
                item.mesh.scale.set(1, 1, 1);
                item.finished = true;
            }
        });

        this.updateAnimationProgress();
        this.updateCamera();
        this.renderer.render(this.scene, this.camera);
    }

    onScenePointerDown(event) {
        this.mouseDown = true;
        this.isDragging = true;
        this.pointerMoved = false;
        this.previousMouseX = event.clientX;
        this.previousMouseY = event.clientY;

        if (this.renderer && this.renderer.domElement) {
            try {
                this.renderer.domElement.setPointerCapture(event.pointerId);
            } catch (_) {}
        }
    }

    onScenePointerMove(event) {
        if (!this.isDragging) return;

        const dx = event.clientX - this.previousMouseX;
        const dy = event.clientY - this.previousMouseY;

        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            this.pointerMoved = true;
        }

        this.cameraAngleX -= dx * 0.008;
        this.cameraAngleY += dy * 0.008;
        this.cameraAngleY = Math.max(0.15, Math.min(1.45, this.cameraAngleY));

        this.previousMouseX = event.clientX;
        this.previousMouseY = event.clientY;
    }

    onScenePointerUp(event) {
        if (!this.mouseDown) return;

        this.mouseDown = false;
        this.isDragging = false;

        if (!this.pointerMoved) {
            this.onSceneClick(event);
        }

        if (this.renderer && this.renderer.domElement) {
            try {
                this.renderer.domElement.releasePointerCapture(event.pointerId);
            } catch (_) {}
        }
    }

    onScenePointerLeave() {
        this.isDragging = false;
        this.mouseDown = false;
    }

    onSceneWheel(event) {
        this.cameraDistance += event.deltaY * 0.012;
        this.cameraDistance = Math.max(1, Math.min(100, this.cameraDistance));
    }

    onSceneClick(event) {
        if (!this.raycaster || !this.camera || !this.renderer) return;

        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const hits = this.raycaster.intersectObjects(this.warehouseObjects, false);

        if (hits.length === 0) {
            this.clearSelectedBox();
            return;
        }

        this.selectBox(hits[0].object);
    }

    selectBox(mesh) {
        if (!mesh || !mesh.userData) return;

        this.selectedMesh = mesh;
        this.selectedBox = mesh.userData;

        const panel = document.getElementById("selectedBoxPanel");
        if (panel) panel.classList.remove("hidden");

        document.getElementById("selectedBoxName").textContent = this.selectedBox.name || "—";
        document.getElementById("selectedLength").textContent = `${this.formatNumber(this.selectedBox.length)} cm`;
        document.getElementById("selectedWidth").textContent = `${this.formatNumber(this.selectedBox.width)} cm`;
        document.getElementById("selectedHeight").textContent = `${this.formatNumber(this.selectedBox.height)} cm`;
        document.getElementById("selectedPosition").textContent = `X: ${this.formatNumber(this.selectedBox.x)} | Y: ${this.formatNumber(this.selectedBox.y)} | Z: ${this.formatNumber(this.selectedBox.z)}`;

        this.resetBoxMaterial();

        if (mesh.material) {
            mesh.material.emissive = new window.THREE.Color(0xffa726);
            mesh.material.emissiveIntensity = 0.65;
        }
    }

    formatNumber(value) {
        return Number(value || 0).toFixed(1);
    }

    resetBoxMaterial() {
        this.warehouseObjects.forEach((mesh) => {
            if (!mesh.material) return;
            mesh.material.emissive = new window.THREE.Color(0x000000);
            mesh.material.emissiveIntensity = mesh.userData.originalEmissive || 0;
        });
    }

    clearSelectedBox() {
        this.resetBoxMaterial();
        this.selectedMesh = null;
        this.selectedBox = null;

        const panel = document.getElementById("selectedBoxPanel");
        if (panel) panel.classList.add("hidden");
    }

    toggleGrid() {
        if (!this.grid) return;
        this.gridVisible = !this.gridVisible;
        this.grid.visible = this.gridVisible;
    }

    resize3D() {
        const container = document.getElementById("scene");
        if (!this.camera || !this.renderer || !container) return;

        const width = container.clientWidth;
        const height = container.clientHeight;
        if (width <= 0 || height <= 0) return;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    downloadExcelTemplate() {
        window.open("/api/excel-template", "_blank");
    }

    async importExcelData(file) {
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/api/excel-import", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const details = await response.text();
                throw new Error(details || "Nie udało się wczytać pliku Excel.");
            }

            const result = await response.json();
            const data = result.data || {};

            if (!data.room_length && !data.room_width && !data.room_height) {
                throw new Error("Plik nie zawiera wymiarów magazynu.");
            }

            document.getElementById("roomLength").value = data.room_length;
            document.getElementById("roomWidth").value = data.room_width;
            document.getElementById("roomHeight").value = data.room_height;

            const packagesList = document.getElementById("packagesList");
            packagesList.innerHTML = "";
            this.packageId = 0;

            (data.packages || []).forEach((item) => {
                this.addPackage();
            });

            const rows = document.querySelectorAll(".package-row");
            (data.packages || []).forEach((item, index) => {
                const row = rows[index];
                if (!row) return;
                row.querySelector(".name").value = item.name || "";
                row.querySelector(".length").value = item.length || 0;
                row.querySelector(".width").value = item.width || 0;
                row.querySelector(".height").value = item.height || 0;
                row.querySelector(".quantity").value = item.quantity || 1;
            });

            this.updateInventory();
            this.updateRoomSidebar();
            this.showView("dashboard");
            alert("Dane z Excela zostały zaimportowane.");
        } catch (error) {
            console.error(error);
            alert(`Błąd importu Excela:\n\n${error.message}`);
        }
    }

    loadDemo() {
        document.getElementById("roomLength").value = 1000;
        document.getElementById("roomWidth").value = 800;
        document.getElementById("roomHeight").value = 300;

        const packagesList = document.getElementById("packagesList");
        packagesList.innerHTML = "";
        this.packageId = 0;

        this.addPackage();
        this.addPackage();
        this.addPackage();

        const rows = document.querySelectorAll(".package-row");
        const data = [
            ["Karton A", 120, 60, 50, 12],
            ["Karton B", 80, 50, 40, 20],
            ["Paczka C", 60, 40, 30, 35],
        ];

        rows.forEach((row, index) => {
            const item = data[index];
            row.querySelector(".name").value = item[0];
            row.querySelector(".length").value = item[1];
            row.querySelector(".width").value = item[2];
            row.querySelector(".height").value = item[3];
            row.querySelector(".quantity").value = item[4];
        });

        this.updateInventory();
        this.updateRoomSidebar();
        this.showView("dashboard");
        setTimeout(() => this.optimize(), 250);
    }
}

window.WarehouseApp = WarehouseApp;
window.warehouseApp = new WarehouseApp();
