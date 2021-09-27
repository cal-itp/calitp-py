docs-build/%.md: docs/%.md
	mkdir -p docs-build
	jupytext --from md --to ipynb --output - $^ \
		| jupyter nbconvert --stdin --to markdown --execute --output $@
