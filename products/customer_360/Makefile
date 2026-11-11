.PHONY: deploy build reset verify
PROFILE ?= DEFAULT
TARGET ?= demo

deploy:
	databricks bundle deploy -t $(TARGET) --profile $(PROFILE)

build:
	databricks bundle run customer_360_build -t $(TARGET) --profile $(PROFILE)

verify:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python verify.py

reset:
	databricks bundle destroy -t $(TARGET) --profile $(PROFILE) --auto-approve
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python reset.py
