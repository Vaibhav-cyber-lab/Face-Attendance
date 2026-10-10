# Attendly — Face Attendance Web App (UI refresh)

This refreshed version improves the interface across the home page, teacher login, dashboard, student registration, live camera, daily attendance, monthly reports, student lookup, and WhatsApp report pages. The layout is responsive for phones and desktops.

## Files
- `app.py` — Flask application and existing attendance routes
- `base.html`, `home.html`, `login.html`, `dashboard.html`, `camera.html`, `attendance.html`, `monthly.html`, `student.html`, `whatsapp.html` — page templates
- `requirements.txt`, `Procfile`, `render.yaml` — deployment configuration

## Important for your current GitHub setup
Your current repository has HTML files at the root, and the deployed app was changed to `template_folder="."`. This refresh keeps that structure so Flask can find the templates without moving them into a folder. Keep the HTML files beside `app.py`.

## Apply the UI update from a phone
1. Download and unzip this project.
2. In your GitHub repository, replace `app.py` and all the root-level `.html` files with the versions from this ZIP. Keep `requirements.txt`, `Procfile`, and `render.yaml` if they already exist and are configured correctly.
3. Commit the changes to the `main` branch.
4. In Render, wait for the deployment to finish, then refresh your website.

## Before real use
- Set a strong `ADMIN_PASSWORD` and a secret `SECRET_KEY` in Render Environment settings. Never publish these values.
- Configure a persistent disk or managed database appropriate to your deployment; otherwise attendance and face data may be lost after redeploy/restart.
- Public student lookup should be protected with student authentication before real records are used.
- Monthly percentages estimate weekdays × 7 periods and do not exclude holidays. Update the sample timetable in `app.py`.
- Face recognition can make mistakes. Obtain appropriate authorization and consent, protect biometric data, and maintain a teacher correction process.
- WhatsApp links are prefilled messages only; a teacher must manually press Send.
- This is a starter project and has not been security-audited or production-validated.

Default password in code if no environment variable is configured: `ChangeMe123!`. Change it before using the site.
