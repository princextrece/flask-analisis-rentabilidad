run:
	flask --app costos2 run

install:
	pip install -r requirements.txt

deploy:
	git add .
	git commit -m "Deploying to Render"
	git push origin main

