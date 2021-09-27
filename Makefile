docs-build/%.md: docs/%.md
	jupytext --from md --to ipynb --output - $^ \
		| jupyter nbconvert --stdin --to markdown --execute --output $@
