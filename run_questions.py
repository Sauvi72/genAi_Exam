import os
from pathlib import Path
from app import ask, print_result

QUESTIONS = [
    {
        "id": 1,
        "question": "On what date were the prices in this catalogue last updated?",
        "k": 8,
        "threshold": 0.20
    },
    {
        "id": 2,
        "question": "In which year was the publisher (Orient BlackSwan) incorporated?",
        "k": 8,
        "threshold": 0.20
    },
    {
        "id": 3,
        "question": "What is the price of a Physics textbook?",
        "k": 6,
        "threshold": 0.25
    },
    {
        "id": 4,
        "question": "Who is the current Minister of Education?",
        "k": 6,
        "threshold": 0.25
    },
    {
        "id": 5,
        "question": 'Which is the "best" history book for a beginner?',
        "k": 6,
        "threshold": 0.25
    }
]

def run_all_questions():
    results = []
    print("=" * 60)
    print("Running QA Evaluation on 5 Questions...")
    print("=" * 60)

    for item in QUESTIONS:
        qid = item["id"]
        q = item["question"]
        k = item.get("k", 6)
        thresh = item.get("threshold", 0.25)

        print(f"\n[Question {qid}]: {q}")
        res = ask(q, k=k, score_threshold=thresh)
        print_result(res)

        results.append({
            "id": qid,
            "question": q,
            "answer": res["answer"],
            "reference": res["pages"],
            "snippet": res["snippet"]
        })

    # Save to answers.md
    output_path = Path(__file__).resolve().parent / "answers.md"
    markdown_content = generate_markdown(results)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print("\n" + "=" * 60)
    print(f"Results successfully saved to {output_path}")
    print("=" * 60)

def generate_markdown(results):
    lines = [
        "# RAG Evaluation Results - Orient BlackSwan History Catalogue 2024-25\n",
        "## Summary Table\n",
        "| # | Question | Answer | Reference |",
        "|---|----------|--------|-----------|"
    ]

    for r in results:
        clean_ans = r['answer'].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {r['id']} | {r['question']} | {clean_ans} | {r['reference']} |")

    lines.append("\n## Detailed Breakdown\n")

    for r in results:
        lines.append(f"### Question {r['id']}: {r['question']}")
        lines.append(f"- **Answer**: {r['answer']}")
        lines.append(f"- **Reference**: {r['reference']}")
        lines.append(f"- **Supporting Snippet**:\n  > {r['snippet']}\n")

    return "\n".join(lines)

if __name__ == "__main__":
    run_all_questions()
