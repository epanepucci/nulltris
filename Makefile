INSTALL_DIR  := $(HOME)/.local/lib/nulltris
BIN_DIR      := $(HOME)/.local/bin
DESKTOP_DIR  := $(HOME)/.local/share/applications
UV           := $(shell command -v uv)

.PHONY: run install uninstall

run:
	uv run python main.py

install:
	@echo "Installing nulltris to $(INSTALL_DIR)..."
	mkdir -p $(INSTALL_DIR) $(BIN_DIR) $(DESKTOP_DIR)
	cp main.py pyproject.toml uv.lock $(INSTALL_DIR)/
	cd $(INSTALL_DIR) && uv sync --quiet
	@printf '#!/bin/sh\nexec %s run --project %s python %s/main.py "$$@"\n' \
		$(UV) $(INSTALL_DIR) $(INSTALL_DIR) > $(BIN_DIR)/nulltris
	chmod +x $(BIN_DIR)/nulltris
	@printf '[Desktop Entry]\nName=Nulltris\nComment=Falling-block puzzle game\nExec=%s/nulltris\nTerminal=false\nType=Application\nCategories=Game;\n' \
		$(BIN_DIR) > $(DESKTOP_DIR)/nulltris.desktop
	update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@echo "Done. Make sure $(BIN_DIR) is on your PATH."

uninstall:
	rm -rf $(INSTALL_DIR)
	rm -f  $(BIN_DIR)/nulltris
	rm -f  $(DESKTOP_DIR)/nulltris.desktop
	update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@echo "Nulltris uninstalled."
