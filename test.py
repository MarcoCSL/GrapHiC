import sys
import argparse
from pathlib import Path
from src.GrapHiC import GrapHiC


def main():
	parser = argparse.ArgumentParser(description="GrapHiC CLI")
	parser.add_argument(
		"input_file",
		nargs="?",
		default="questions.txt",
		help="Input file path required if not in interactive mode"
	)
	parser.add_argument(
        "-i", "-inter", "-interactive",
        action="store_true",
        dest="interactive",
        help="Run in interactive mode"
    )
	parser.add_argument(
		"-q", "-quiet",
		action="store_true",
		dest="quiet",
		help="Minimal output, does not show utilized queries"
	)
	parser.add_argument(
		"--llm",
		default="openai/gpt-oss-20b"
	)

	args = parser.parse_args()

	graphic = GrapHiC(args.llm)

	base_path = Path(__file__).parent
	answer_path = base_path / "answers.txt"
	complete_answer_path = base_path / "complete_answers.txt"

	if args.interactive:
		with answer_path.open("a", encoding="utf-8") as answer_file, \
			 complete_answer_path.open("a", encoding="utf-8") as complete_file:

			while True:
				try:
					question = input("Ask your question:\n")
					result, query = graphic.answer(question)

					print("\n", result)
					if not args.quiet:
						print("Used query:\n", query, "\n")

					answer_file.write(question + "\n" + result + "\n\n")
					answer_file.flush()

					complete_file.write(
						question + "\n" +
						result + "\n" +
						"Query:\n" + query + "\n\n"
					)
					complete_file.flush()

				except KeyboardInterrupt:
					print("\nInterrupted by user.")
					break

	else:
		questions_path = base_path / args.input_file

		if not questions_path.exists():
			print("questions.txt not found.")
			return

		with questions_path.open("r", encoding="utf-8") as q_file, \
			 answer_path.open("w", encoding="utf-8") as answer_file, \
			 complete_answer_path.open("w", encoding="utf-8") as complete_file:

			for line in q_file:
				question = line.strip()
				if not question:
					continue

				result, query = graphic.answer(question)

				answer_file.write(question + "\n" + result + "\n\n")
				answer_file.flush()

				complete_file.write(
					question + "\n" +
					result + "\n" +
					"Query:\n" + query + "\n\n"
				)
				complete_file.flush()

		print(f"Answers written to {answer_path}")
		print(f"Complete answers written to {complete_answer_path}")


if __name__ == "__main__":
	main()
