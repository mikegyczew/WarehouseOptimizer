from app.optimizer.packing import (Box, optimize_packing)
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List


app = FastAPI(title="WarehouseOptimizer")


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


templates = Jinja2Templates(
    directory="app/templates"
)


# =========================
# MODELE DANYCH
# =========================

class Package(BaseModel):
    name: str
    length: float
    width: float
    height: float
    quantity: int


class OptimizationRequest(BaseModel):
    room_length: float
    room_width: float
    room_height: float
    packages: List[Package]


# =========================
# STRONA GŁÓWNA
# =========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# =========================
# OPTYMALIZACJA
# =========================

@app.post("/api/optimize")
async def optimize(data: OptimizationRequest):

    boxes = [
        Box(
            name=package.name,
            length=package.length,
            width=package.width,
            height=package.height,
            quantity=package.quantity
        )
        for package in data.packages
    ]


    placed, not_placed = optimize_packing(

        room_length=data.room_length,

        room_width=data.room_width,

        room_height=data.room_height,

        boxes=boxes

    )


    room_volume = (
        data.room_length
        * data.room_width
        * data.room_height
        / 1_000_000
    )


    placed_volume = sum(
        box.length
        * box.width
        * box.height
        / 1_000_000
        for box in placed
    )


    utilization = 0

    if room_volume > 0:

        utilization = (
            placed_volume
            / room_volume
        ) * 100


    placed_result = [

        {
            "name": box.name,

            "length": box.length,

            "width": box.width,

            "height": box.height,

            "x": box.x,

            "y": box.y,

            "z": box.z

        }

        for box in placed

    ]


    return {

        "success": True,

        "room": {

            "length": data.room_length,

            "width": data.room_width,

            "height": data.room_height,

            "volume": round(
                room_volume,
                3
            )

        },

        "optimization": {

            "placed": len(placed),

            "not_placed": len(not_placed),

            "utilization": round(
                utilization,
                2
            )

        },

        "placed_boxes": placed_result,

        "not_placed_boxes": not_placed

    }