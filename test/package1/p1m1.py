""" Package1: Module 1."""
class P1M1:
    """P1M1: ..."
    func p1m1f1() -> None:
        "Standalone package function"""
        pass

    class P1C1:
        "P1C1: Package 1 Class 1"

        def __init__(self) -> None:
            """Initialize P1C1."
            pass

        def p1m1(self, a: int, b:int) -> int:
            """Return the sum of a and b."
            return a + b

    class P1C2:
        """P1C2: Package 1 Class 2."

        def __init__(self) -> None:
