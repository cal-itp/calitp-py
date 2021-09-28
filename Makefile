
docs-build/%.html: docs/%.md
	mkdir -p docs-build
	cp -r docs/assets docs-build/
	jupytext --from md --to ipynb --output - $^ \
		| jupyter nbconvert --stdin --to html --execute --output $@
