import pandas as pd

df = pd.read_csv("./data/learn-hist/learn-hist.csv")
# learn-hist.csv columns:
# student_id           # 학생 ID
# question_code        # 문항 ID
# correct              # 정오답 여부
# event_time           # 학습 시간 (예. 2025-01-01 00:00:01)
# ---
# question_grad_unit   # 문항의 학년/학기/단원/차시 정보 (예. GR15_1_1_1)
# question_difficulty  # 문항 난이도
# question_correct     # 문항 정답률


def lesson_based(df, only_correct = False):
    sequences = {}
    for index, row in df.iterrows():
        if pd.isna(row["question_grad_unit"]):
            continue

        grad_unit = row["question_grad_unit"].split("_")
        student_id_grad_unit = (
            row["student_id"] * 10000
            + int(grad_unit[0][3]) * 1000
            + int(grad_unit[1]) * 100
            + int(grad_unit[2]) * 10
            + int(grad_unit[3])
        )

        if student_id_grad_unit not in sequences:
            sequences[student_id_grad_unit] = []
        sequences[student_id_grad_unit].append(row["question_code"])

    users = 0
    items = set()
    actions = 0
    with open("./data/learn-hist/lesson-based.txt", "w") as file:
        for id, qc_list in sequences.items(): # student_id, question_code
            if len(qc_list) < 5:
                continue

            users += 1
            actions += len(qc_list)
            for qc in qc_list:
                file.write(f"{id} {qc}\n")
                items.add(qc)


def unit_based(df, only_correct=False):
    sequences = {}
    for index, row in df.iterrows():
        if pd.isna(row["question_grad_unit"]):
            continue
        elif only_correct and row["correct"] == 0:
            continue

        grad_unit = row["question_grad_unit"].split("_")
        student_id_grad_unit = (
            row["student_id"] * 1000
            + int(grad_unit[0][3]) * 100
            + int(grad_unit[1]) * 10
            + int(grad_unit[2])
        )

        if student_id_grad_unit not in sequences:
            sequences[student_id_grad_unit] = []
        sequences[student_id_grad_unit].append(row["question_code"])

    users = 0
    items = set()
    actions = 0
    with open("./data/learn-hist/unit-based-OC.txt", "w") as file:
        for id, qc_list in sequences.items():  # student_id, question_code
            if len(qc_list) < 5:
                continue

            users += 1
            actions += len(qc_list)
            for qc in qc_list:
                file.write(f"{id} {qc}\n")
                items.add(qc)

    print("#users:", users)
    print("#items:", len(items))
    print("#actions:", actions)
    print("Avg. length:", actions/users)


if __name__ == "__main__":
    # lesson_based(df)
    # #users: 812,968
    # #items: 3,936
    # #actions: 15.3M
    # Avg.length: 18.8
    
    unit_based(df, True)
