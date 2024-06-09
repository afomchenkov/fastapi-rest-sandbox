def get_full_name(first_name: str, last_name: str):
    full_name = first_name.title() + " " + last_name.title()
    return full_name


def process_items(items: list[str]):
    for item in items:
        print(item)


def process_items_tuple(items_t: tuple[int, int, str], items_s: set[bytes]):
    return items_t, items_s


def process_item_union(item: int | str):
    print(item)


def process_items(prices: dict[str, float]):
    for item_name, item_price in prices.items():
        print(item_name)
        print(item_price)
