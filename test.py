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
	args = parser.parse_args()

	graphic = GrapHiC()

	if args.interactive:
		while True:
			try:
				question = input("Ask your question:\n")
				result, query = graphic.answer(question)
				
				print("\n", result)
				if not args.quiet:
					print("Used query:\n", query, "\n")

			except KeyboardInterrupt:
				print("\nInterrupted by user.")
				break
	else:
		base_path = Path(__file__).parent
		questions_path = base_path / "questions.txt"
		answers_path = base_path / "answers.txt"

		if not questions_path.exists():
			print("question.txt not found.")
			return

		with questions_path.open("r", encoding="utf-8") as q_file, \
			 answers_path.open("w", encoding="utf-8") as a_file:

			for line in q_file:
				question = line.strip()
				if not question:
					continue

				result, query = graphic.answer(question)

				a_file.write(question + "\n" + result + "\n")
				if not args.quiet:
					a_file.write("\nUsing query:\n" + query)
				a_file.write("\n\n\n")
				a_file.flush()

		print(f"Answers written to {answers_path}")


if __name__ == "__main__":
	main()
