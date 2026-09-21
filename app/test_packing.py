from io import BytesIO

from openpyxl import Workbook

from main import ExcelExportService, ExcelImportService
from optimizer.packing import Box, optimize_packing


def test_optimize_packing_places_compatible_boxes():
    boxes = [
        Box(name="A", length=50, width=40, height=30, quantity=2),
        Box(name="B", length=30, width=20, height=20, quantity=2),
    ]

    placed, not_placed = optimize_packing(
        room_length=200,
        room_width=200,
        room_height=200,
        boxes=boxes,
    )

    assert len(not_placed) == 0
    assert len(placed) == 4
    assert all(box.length > 0 for box in placed)


def test_excel_import_parses_room_and_packages():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Warehouse"
    sheet.append(["room_length", "room_width", "room_height"])
    sheet.append([200, 180, 150])
    sheet.append([])
    sheet.append(["name", "length", "width", "height", "quantity"])
    sheet.append(["A", 50, 40, 30, 2])
    sheet.append(["B", 30, 20, 20, 3])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    data = ExcelImportService.parse_excel(buffer.read())

    assert data["room_length"] == 200
    assert data["room_width"] == 180
    assert data["room_height"] == 150
    assert data["packages"][0]["name"] == "A"
    assert data["packages"][1]["quantity"] == 3


def test_history_service_persists_optimization_run():
    from main import OptimizationHistoryService, OptimizationRequest, Package

    request = OptimizationRequest(
        room_length=200,
        room_width=180,
        room_height=150,
        packages=[
            Package(name="A", length=50, width=40, height=30, quantity=2),
            Package(name="B", length=30, width=20, height=20, quantity=1),
        ],
    )

    result = {
        "success": True,
        "optimization": {"placed": 2, "not_placed": 1, "utilization": 25.5},
        "room": {"length": 200, "width": 180, "height": 150, "volume": 5.4},
        "placed_boxes": [{"name": "A", "length": 50, "width": 40, "height": 30, "x": 0, "y": 0, "z": 0}],
        "not_placed_boxes": ["B"],
    }

    run_id = OptimizationHistoryService.save_run(request, result)
    history = OptimizationHistoryService.list_recent(limit=5)

    assert run_id is not None
    assert any(item["id"] == run_id for item in history)
    assert any(item["placed_count"] == 2 for item in history)


def test_history_service_gets_single_run():
    from main import OptimizationHistoryService, OptimizationRequest, Package

    request = OptimizationRequest(
        room_length=300,
        room_width=200,
        room_height=180,
        packages=[Package(name="C", length=60, width=50, height=40, quantity=3)],
    )
    result = {
        "success": True,
        "optimization": {"placed": 3, "not_placed": 0, "utilization": 40.0},
        "room": {"length": 300, "width": 200, "height": 180, "volume": 10.8},
        "placed_boxes": [{"name": "C", "length": 60, "width": 50, "height": 40, "x": 0, "y": 0, "z": 0}],
        "not_placed_boxes": [],
    }

    run_id = OptimizationHistoryService.save_run(request, result)
    item = OptimizationHistoryService.get_run(run_id)

    assert item is not None
    assert item["id"] == run_id
    assert item["room_length"] == 300


def test_excel_export_builds_workbook_for_history_item():
    from main import OptimizationHistoryService, OptimizationRequest, Package

    request = OptimizationRequest(
        room_length=220,
        room_width=180,
        room_height=160,
        packages=[
            Package(name="P1", length=50, width=40, height=30, quantity=2),
            Package(name="P2", length=30, width=20, height=20, quantity=1),
        ],
    )
    result = {
        "success": True,
        "optimization": {"placed": 3, "not_placed": 0, "utilization": 42.5},
        "room": {"length": 220, "width": 180, "height": 160, "volume": 6.336},
        "placed_boxes": [{"name": "P1", "length": 50, "width": 40, "height": 30, "x": 0, "y": 0, "z": 0}],
        "not_placed_boxes": [],
    }

    run_id = OptimizationHistoryService.save_run(request, result)
    item = OptimizationHistoryService.get_run(run_id)

    workbook = ExcelExportService.build_run_workbook(item)
    sheet = workbook.active

    values = [value for row in sheet.iter_rows(values_only=True) for value in row]
    assert "Run ID" in values
    assert "room_length" in values
    assert "P1" in values
