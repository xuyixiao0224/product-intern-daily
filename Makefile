.PHONY: test doctor demo validate site readme clean

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

doctor:
	python3 run.py doctor

demo:
	python3 run.py search --role AI产品 --base 北京 --out candidates.json
	python3 run.py fetch candidates.json --out details --limit 3

validate:
	python3 scripts/validate_data.py data/jobs.example.json

site:
	python3 scripts/build_site.py data/jobs.example.json docs/index.html

readme:
	python3 scripts/generate_readme.py data/jobs.example.json docs/JOBS.md

feed:
	python3 scripts/build_feed.py data/jobs.example.json docs/feed.xml "https://example.github.io/product-intern-daily/"

clean:
	rm -rf data details exports images dist candidates.json tasks.json extractions.json
