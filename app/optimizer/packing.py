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


def boxes_overlap(a: PlacedBox, b: PlacedBox) -> bool:

    return not (
        a.x + a.length <= b.x
        or b.x + b.length <= a.x
        or a.y + a.width <= b.y
        or b.y + b.width <= a.y
        or a.z + a.height <= b.z
        or b.z + b.height <= a.z
    )


def fits_inside(
    box: PlacedBox,
    room_length: float,
    room_width: float,
    room_height: float
) -> bool:

    return (
        box.x + box.length <= room_length
        and
        box.y + box.width <= room_width
        and
        box.z + box.height <= room_height
    )


def can_place(
    box: PlacedBox,
    placed: list[PlacedBox],
    room_length: float,
    room_width: float,
    room_height: float
) -> bool:

    if not fits_inside(
        box,
        room_length,
        room_width,
        room_height
    ):
        return False

    for existing in placed:

        if boxes_overlap(box, existing):
            return False

    return True


def generate_positions(
    placed: list[PlacedBox]
) -> list[tuple[float, float, float]]:

    positions = {
        (0, 0, 0)
    }

    for box in placed:

        positions.add(
            (
                box.x + box.length,
                box.y,
                box.z
            )
        )

        positions.add(
            (
                box.x,
                box.y + box.width,
                box.z
            )
        )

        positions.add(
            (
                box.x,
                box.y,
                box.z + box.height
            )
        )

    return sorted(
        positions,
        key=lambda position: (
            position[2],
            position[1],
            position[0]
        )
    )


def optimize_packing(
    room_length: float,
    room_width: float,
    room_height: float,
    boxes: list[Box]
) -> tuple[list[PlacedBox], list[str]]:

    placed: list[PlacedBox] = []
    not_placed: list[str] = []


    # Najpierw próbujemy układać największe paczki.
    boxes_to_place = sorted(
        boxes,
        key=lambda box:
        box.length * box.width * box.height,
        reverse=True
    )


    for box in boxes_to_place:

        for number in range(1, box.quantity + 1):

            successfully_placed = False


            # Próbujemy wszystkie 6 orientacji.
            orientations = list(
                dict.fromkeys(
                    permutations(
                        (
                            box.length,
                            box.width,
                            box.height
                        )
                    )
                )
            )


            positions = generate_positions(
                placed
            )


            for length, width, height in orientations:

                if successfully_placed:
                    break


                for x, y, z in positions:

                    candidate = PlacedBox(
                        name=box.name,
                        length=length,
                        width=width,
                        height=height,
                        x=x,
                        y=y,
                        z=z
                    )


                    if can_place(
                        candidate,
                        placed,
                        room_length,
                        room_width,
                        room_height
                    ):

                        placed.append(candidate)

                        successfully_placed = True

                        break


            if not successfully_placed:

                not_placed.append(
                    f"{box.name} #{number}"
                )


    return placed, not_placed