import json
from time import perf_counter


EPSILON = 1e-9
REPEAT_COUNT = 10
FILTER_LABELS = {"cross": "Cross", "x": "X"}
EXPECTED_LABELS = {"+": "Cross", "x": "X"}

def normalize_label(raw_label, labels):
    """주어진 JSON 라벨을 표준 라벨로 변환한다."""
    if not isinstance(raw_label, str) or raw_label not in labels:
        raise ValueError(f"알 수 없는 라벨 ({raw_label!r})")
    return labels[raw_label]


def mac(pattern, filter_data):
    score = 0.0

    for i in range(len(pattern)):
        for j in range(len(pattern[i])):
            score += pattern[i][j] * filter_data[i][j]

    return score


def flatten_matrix(matrix):
    flat = []
    for row in matrix:
        flat.extend(row)
    return flat


def mac_1d(pattern, filter_data):
    score = 0.0
    for index in range(len(pattern)):
        score += pattern[index] * filter_data[index]
    return score


def generate_pattern(N, shape):
    pattern = []
    center = N // 2

    for i in range(N):
        row = []

        for j in range(N):
            value = 0

            if shape == "Cross":
                if i == center or j == center:
                    value = 1

            elif shape == "X":
                if i == j or i + j == N - 1:
                    value = 1

            row.append(value)

        pattern.append(row)

    return pattern


def input_matrix(name):
    matrix = []
    print(f"\n{name} 입력 (3×3)")

    for i in range(3):
        while True:
            data = input(f"{i + 1}번째 행: ")
            values = data.split()

            if len(values) != 3:
                print("오류: 숫자 3개를 입력하세요.")
                continue

            try:
                row = []
                for value in values:
                    row.append(float(value))
            except ValueError:
                print("오류: 숫자만 입력하세요.")
                continue

            matrix.append(row)
            break

    return matrix


def run_user_mode():
    print("\n필터 입력 방식")
    print("1. 필터 A와 B 직접 입력")
    print("2. Cross와 X 필터 자동 생성")

    while True:
        filter_choice = input("선택: ").strip()
        if filter_choice in ("1", "2"):
            break
        print("1 또는 2를 입력하세요.")

    if filter_choice == "1":
        filter_a = input_matrix("필터 A")
        filter_b = input_matrix("필터 B")
    else:
        filter_a = generate_pattern(3, "Cross")
        filter_b = generate_pattern(3, "X")
        print("필터 A는 Cross, 필터 B는 X로 생성했습니다.")

    print("\n필터 A와 B를 저장했습니다.")

    user_pattern = input_matrix("입력 패턴")

    repeat_count = REPEAT_COUNT

    # 입력 완료 후, 두 필터를 채점하는 반복 구간을 측정한다.
    start = perf_counter()
    for _ in range(repeat_count):
        score_a = mac(user_pattern, filter_a)
        score_b = mac(user_pattern, filter_b)
    end = perf_counter()  # 판정과 출력 전에 측정을 끝낸다.

    average_ms = (end - start) * 1000 / repeat_count

    if abs(score_a - score_b) < EPSILON:
        result = "판정 불가"
    elif score_a > score_b:
        result = "A"
    else:
        result = "B"

    print("\nMAC 연산 결과")
    print("필터 A 점수:", score_a)
    print("필터 B 점수:", score_b)
    print("판정 결과:", result)
    print(f"MAC 평균 연산 시간 (A·B 채점, {repeat_count}회): {average_ms:.6f} ms")
    print_mac_benchmark((3,))


def is_square_matrix(matrix, size):
    if not isinstance(matrix, list) or len(matrix) != size:
        return False

    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            return False

    return True


def print_mac_benchmark(sizes=(3, 5, 13, 25)):
    repeat_count = REPEAT_COUNT

    print(f"\nMAC 성능 분석 (각 평균/{repeat_count}회)")
    print(f'{"N×N":>7} {"2D (ms)":>12} {"1D (ms)":>12} {"MAC (N²)":>12}')

    for size in sizes:
        pattern = generate_pattern(size, "X")
        cross_filter = generate_pattern(size, "Cross")
        flat_pattern = flatten_matrix(pattern)
        flat_filter = flatten_matrix(cross_filter)

        # 배열 준비가 끝난 뒤 각 MAC의 반복 구간만 측정한다.
        start = perf_counter()
        for _ in range(repeat_count):
            score_2d = mac(pattern, cross_filter)
        average_2d_ms = (perf_counter() - start) * 1000 / repeat_count

        start = perf_counter()
        for _ in range(repeat_count):
            score_1d = mac_1d(flat_pattern, flat_filter)
        average_1d_ms = (perf_counter() - start) * 1000 / repeat_count

        operation_count = size ** 2
        print(f"{f'{size}×{size}':>7} {average_2d_ms:>12.6f} "
              f"{average_1d_ms:>12.6f} {operation_count:>12}")

        if score_2d != score_1d:
            print(f"  점수 불일치: 2차원 {score_2d}, 1차원 {score_1d}")


def run_json_mode():
    try:
        with open("data.json", encoding="utf-8") as file:
            data = json.load(file)
    except OSError as error:
        print(f"data.json 파일을 열 수 없습니다. ({error})")
        return
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"data.json 내용을 읽을 수 없습니다. ({error})")
        return

    if not isinstance(data, dict):
        print("데이터 형식 오류: JSON 최상위 값은 객체여야 합니다.")
        return

    filters = data.get("filters")
    patterns = data.get("patterns")

    if not isinstance(filters, dict) or not isinstance(patterns, dict):
        print("데이터 형식 오류: filters와 patterns가 모두 객체여야 합니다.")
        return
    failures = {}

    for pattern_key, pattern_data in patterns.items():
        try:
            prefix, size_text, case_number = pattern_key.split("_")
            if prefix != "size" or not size_text.isdecimal() or not case_number.isdecimal():
                raise ValueError("패턴 이름은 size_5_1처럼 작성해야 합니다.")

            size = int(size_text)
            filter_key = f"size_{size}"

            selected_filters = filters[filter_key]
            standard_filters = {
                normalize_label(key, FILTER_LABELS): selected_filters[key]
                for key in FILTER_LABELS
            }
            input_pattern = pattern_data["input"]
        except (ValueError, KeyError, TypeError) as error:
            failures[pattern_key] = f"데이터 형식 오류 ({error})"
            print(f"{pattern_key}: FAIL ({failures[pattern_key]})")
            continue

        matrices = (
            ("입력 패턴", input_pattern),
            ("Cross 필터", standard_filters["Cross"]),
            ("X 필터", standard_filters["X"]),
        )
        for name, matrix in matrices:
            if not is_square_matrix(matrix, size):
                failures[pattern_key] = f"{name}의 크기가 {size}×{size}가 아닙니다."
                break
            if any(type(value) not in (int, float) for row in matrix for value in row):
                failures[pattern_key] = f"{name}에 정수 또는 실수가 아닌 값이 있습니다."
                break

        if pattern_key in failures:
            print(f"{pattern_key}: FAIL ({failures[pattern_key]})")
            continue

        cross_score = mac(input_pattern, standard_filters["Cross"])
        x_score = mac(input_pattern, standard_filters["X"])

        if abs(cross_score - x_score) < EPSILON:
            predicted = "UNDECIDED"
        elif cross_score > x_score:
            predicted = "Cross"
        else:
            predicted = "X"

        raw_expected = pattern_data.get("expected")

        try:
            expected = normalize_label(raw_expected, EXPECTED_LABELS)
        except ValueError:
            failures[pattern_key] = f"잘못된 expected 값 ({raw_expected!r})"
            print(f"{pattern_key}: FAIL ({failures[pattern_key]})")
            continue

        if predicted == expected:
            status = "PASS"
        else:
            status = "FAIL"
            failures[pattern_key] = f"기대값 {expected}, 실제 판정 {predicted}"

        print(f"{pattern_key} ({size}×{size})")
        print(f"  Cross 점수: {cross_score}")
        print(f"  X 점수: {x_score}")
        print(f"  판정: {predicted} / 기대값: {expected} / {status}")

    print_mac_benchmark()
    total_count = len(patterns)
    fail_count = len(failures)
    pass_count = total_count - fail_count

    print(f"\n분석 요약: 총 {total_count}건 / 통과 {pass_count}건 / 실패 {fail_count}건")

    for pattern_key, reason in failures.items():
        print(f"실패 케이스 {pattern_key}: {reason}")


def run_generator_mode():
    while True:
        try:
            size = int(input("패턴 크기 N (3 이상의 홀수): "))
        except ValueError:
            print("정수를 입력하세요.")
            continue

        if size >= 3 and size % 2 == 1:
            break
        print("3 이상의 홀수를 입력하세요.")

    for shape in ("Cross", "X"):
        print(f"\n{shape} ({size}×{size})")
        for row in generate_pattern(size, shape):
            print(*row)


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3×3)")
    print("2. data.json 분석")
    print("3. Cross·X 패턴 생성")

    choice = input("선택: ").strip()
    if choice == "1":
        run_user_mode()
    elif choice == "2":
        run_json_mode()
    elif choice == "3":
        run_generator_mode()
    else:
        print("1, 2 또는 3을 입력하세요.")


if __name__ == "__main__":
    main()
