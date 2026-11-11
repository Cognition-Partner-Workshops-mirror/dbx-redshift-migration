.PHONY: deploy build reset verify dashboard-json verify-dashboard
PROFILE ?= DEFAULT
TARGET ?= demo

deploy: verify-dashboard
	databricks bundle deploy -t $(TARGET) --profile $(PROFILE)

dashboard-json:
	python build_dashboard.py

verify-dashboard:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python verify_dashboard.py

build:
	databricks bundle run customer_360_build -t $(TARGET) --profile $(PROFILE)

verify:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python verify.py

reset:
	databricks bundle destroy -t $(TARGET) --profile $(PROFILE) --auto-approve
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python reset.py
