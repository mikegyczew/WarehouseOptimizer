from dataclasses import dataclass
from itertools import permutations


@dataclass
class Box:
    name: str
    length: float
    width: float
    height: float
    quantity: int


@dataclass
class PlacedBox:
    name: str
    length: float
    width: float
    height: float
    x: float
    y: float
    z: float


class BoxCollisionChecker:
    @staticmethod
    def boxes_overlap(a: PlacedBox, b: PlacedBox) -> bool:
        return not (
            a.x + a.length <= b.x
            or b.x + b.length <= a.x
            or a.y + a.width <= b.y
            or b.y + b.width <= a.y
            or a.z + a.height <= b.z
            or b.z + b.height <= a.z
        )

    @staticmethod
    def fits_inside(
        box: PlacedBox,
        room_length: float,
        room_width: float,
        room_height: float,
    ) -> bool:
        return (
            box.x + box.length <= room_length
            and box.y + box.width <= room_width
            and box.z + box.height <= room_height
        )

    @classmethod
    def can_place(
        cls,
        box: PlacedBox,
        placed: list[PlacedBox],
        room_length: float,
        room_width: float,
        room_height: float,
    ) -> bool:
        if not cls.fits_inside(box, room_length, room_width, room_height):
            return False

        for existing in placed:
            if cls.boxes_overlap(box, existing):
                return False

        return True


class PositionGenerator:
    @staticmethod
    def generate_positions(placed: list[PlacedBox]) -> list[tuple[float, float, float]]:
        positions = {(0, 0, 0)}

        for box in placed:
            positions.add((box.x + box.length, box.y, box.z))
            positions.add((box.x, box.y + box.width, box.z))
            positions.add((box.x, box.y, box.z + box.height))

        return sorted(positions, key=lambda position: (position[2], position[1], position[0]))


class PackingOptimizer:
    def __init__(
        self,
        room_length: float,
        room_width: float,
        room_height: float,
        boxes: list[Box],
    ):
        self.room_length = room_length
        self.room_width = room_width
        self.room_height = room_height
        self.boxes = boxes

    def _sorted_boxes(self) -> list[Box]:
        return sorted(
            self.boxes,
            key=lambda box: box.length * box.width * box.height,
            reverse=True,
        )

    @staticmethod
    def _orientations(box: Box) -> list[tuple[float, float, float]]:
        return list(
            dict.fromkeys(
                permutations((box.length, box.width, box.height))
            )
        )

    def _try_place_box(self, placed: list[PlacedBox], box: Box) -> tuple[bool, PlacedBox | None]:
        for length, width, height in self._orientations(box):
            for x, y, z in PositionGenerator.generate_positions(placed):
                candidate = PlacedBox(
                    name=box.name,
                    length=length,
                    width=width,
                    height=height,
                    x=x,
                    y=y,
                    z=z,
                )

                if BoxCollisionChecker.can_place(
                    candidate,
                    placed,
                    self.room_length,
                    self.room_width,
                    self.room_height,
                ):
                    return True, candidate

        return False, None

    def optimize(self) -> tuple[list[PlacedBox], list[str]]:
        placed: list[PlacedBox] = []
        not_placed: list[str] = []

        for box in self._sorted_boxes():
            for number in range(1, box.quantity + 1):
                was_placed, candidate = self._try_place_box(placed, box)

                if was_placed and candidate is not None:
                    placed.append(candidate)
                    continue

                not_placed.append(f"{box.name} #{number}")

        return placed, not_placed


def optimize_packing(
    room_length: float,
    room_width: float,
    room_height: float,
    boxes: list[Box],
) -> tuple[list[PlacedBox], list[str]]:
    optimizer = PackingOptimizer(
        room_length=room_length,
        room_width=room_width,
        room_height=room_height,
        boxes=boxes,
    )
    return optimizer.optimize()