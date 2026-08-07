TEST_CASES = [

    # ---------- Duplicates ----------
    (
        "Driver likes coffee",
        "I love coffee",
        "duplicate",
    ),

    (
        "Coffee is my favorite beverage",
        "I enjoy cappuccino",
        "duplicate",
    ),

    (
        "I prefer dark mode",
        "Dark mode is my preference",
        "duplicate",
    ),

    (
        "I study Python every evening",
        "Every evening I learn Python",
        "duplicate",
    ),

    # ---------- Related ----------
    (
        "Driver likes coffee",
        "I drink tea",
        "related",
    ),

    (
        "I study Python",
        "I study programming",
        "related",
    ),

    (
        "I own a Tesla",
        "I drive an electric car",
        "related",
    ),

    # ---------- Unrelated ----------
    (
        "Driver likes coffee",
        "I play football",
        "different",
    ),

    (
        "I study Python",
        "I own a dog",
        "different",
    ),

    (
        "Dark mode",
        "Pizza is delicious",
        "different",
    ),
]