import pandas as pd
import json
import random

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


def stu_based(df, only_correct=False, prced=False):
    # Read question-meta file
    with open("./data/learn-hist_resources/question_meta.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    sequences = {}
    starters = {}
    for index, row in df.iterrows():
        if pd.isna(row["question_grad_unit"]):
            continue
        elif only_correct and row["correct"] == 0:
            continue

        if row["student_id"] not in sequences:
            sequences[row["student_id"]] = []

        if prced and len(sequences[row["student_id"]]) > 0:
            prev_question_code = sequences[row["student_id"]][-1]
            question_meta = data[str(prev_question_code)]
            prev_question_grad_unit = f"{question_meta['grad_cd']}_{question_meta['smst_cd']}_{question_meta['unit_order']}_{question_meta['lesn_order']}"

            if row["question_grad_unit"] != prev_question_grad_unit:
                if row["question_grad_unit"] not in starters:
                    starters[row["question_grad_unit"]] = []
                starters[row["question_grad_unit"]].append(row["question_code"])

        sequences[row["student_id"]].append(row["question_code"])

    if prced:
        for k in starters.keys():
            starter_list = starters[k]
            most_common = max(starter_list, key=starter_list.count)
            starters[k] = most_common

        starters = dict(sorted(starters.items()))

        with open("./data/learn-hist_resources/lesson_starters.json", "w", encoding="utf-8") as file:
            json.dump(starters, file, ensure_ascii=False, indent=4)

        delete = []
        for k in sequences.keys():
            if len(sequences[k]) >= 55:
                rv = random.randint(55, len(sequences[k]))
                sequences[k] = sequences[k][rv-55:rv]

            prev_question_code = sequences[k][-1]
            question_meta = data[str(prev_question_code)]
            prev_question_grad_unit = f"{question_meta['grad_cd']}_{question_meta['smst_cd']}_{question_meta['unit_order']}_{question_meta['lesn_order']}"

            grad_cd, smst_cd, unit_order, lesn_order = prev_question_grad_unit.split("_")
            if (
                f"{grad_cd}_{smst_cd}_{unit_order}_{int(lesn_order)+1}"
                in starters.keys()
            ):
                sequences[k].append(starters[f"{grad_cd}_{smst_cd}_{unit_order}_{int(lesn_order)+1}"])
            elif f"{grad_cd}_{smst_cd}_{int(unit_order)+1}_{1}" in starters.keys():
                sequences[k].append(starters[f"{grad_cd}_{smst_cd}_{int(unit_order)+1}_{1}"])
            elif smst_cd == 1:
                sequences[k].append(starters[f"{grad_cd}_{2}_{1}_{1}"])
            elif grad_cd == "GR15":
                sequences[k].append(starters[f"GR16_{1}_{1}_{1}"])
            else:
                delete.append(k)

        for k in delete:
            del sequences[k]

    users = 0
    items = set()
    actions = 0
    with open("./data/learn-hist/stu-based-prced.txt", "w") as file:
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
    print("Avg. length:", actions / users)


if __name__ == "__main__":
    # lesson_based(df)
    # #users: 812,968
    # #items: 3,936
    # #actions: 15.3M
    # Avg.length: 18.8

    # unit_based(df, True)
    # #users: 199,114
    # #items: 3,923
    # #actions: 9.2M
    # Avg.length: 46.5

    stu_based(df, False, True)
    # #users: 14,718
    # #items: 2,063
    # #actions: 0.7M
    # Avg.length: 53.3
