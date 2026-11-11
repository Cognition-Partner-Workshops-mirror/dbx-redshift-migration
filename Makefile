.PHONY: check seed db-setup db-reset validate validate-all legacy-all capture-golden

check:
	ruff check . && pytest && python tools/check_manifest.py

.PHONY: consumer-setup consumer-parity consumer-reset
consumer-setup:
	python -m validation.consumer_parity --setup

consumer-parity:
	python -m validation.consumer_parity --mode $(MODE)

consumer-reset:
	bash tools/consumer_reset.sh $(ARGS)

seed:
	python data/seed/generate_seed.py

db-setup:
	python tools/databricks_setup.py

db-reset:
	python tools/databricks_setup.py --reset

validate:
	python -m validation.validate_unit --unit $(UNIT)

validate-all:
	@set -e; failed=""; \
	for u in $$(python -c "import yaml; m=yaml.safe_load(open('.migration/units.yaml')); \
	  print(' '.join(u for w in m['waves'] for u in w['units']))"); do \
	  if [ -f "$$(python -c "import yaml; m=yaml.safe_load(open('.migration/units.yaml')); \
	    print(m['units']['$$u']['target_dir'])")/etl.sql" ]; then \
	    echo "== validating $$u"; \
	    python -m validation.validate_unit --unit $$u || failed="$$failed $$u"; \
	  fi; \
	done; \
	if [ -n "$$failed" ]; then echo "FAILED:$$failed"; exit 1; fi; \
	echo "all validated units PASS"

legacy-all:
	python tools/legacy_redshift.py all

capture-golden:
	python tools/legacy_redshift.py capture
