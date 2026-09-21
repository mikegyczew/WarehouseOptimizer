from io import BytesIO

from openpyxl import Workbook

from main import ExcelImportService
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
