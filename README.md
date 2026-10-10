# Face Attendance Web Starter

This converts the desktop idea into a browser-based starter for phone and computer access.

## Included
- Teacher/admin login
- Student registration with a clear face photo and WhatsApp number
- OpenCV LBPH model training and camera-based attendance in a browser
- Seven sample class periods
- Daily attendance records
- Monthly report and CSV export
- Prefilled WhatsApp report links (manual sending)

## Important before real use
- Change the sample period times in `app.py` to your college's actual timetable.
- Monthly percentages estimate weekdays × 7 periods; they do not exclude holidays or closed days.
- WhatsApp is not automatic; a teacher must press Send. Automatic sending needs WhatsApp Business API setup.
- This starter uses a single admin password and SQLite. Student lookup is public by roll number. Add proper teacher/student accounts, authorization, privacy controls and a managed database before putting real student data online.
- Face recognition can be wrong. Test carefully, get appropriate consent, and keep a manual attendance fallback.
- Render uses a persistent disk configuration in `render.yaml`; confirm current plan pricing before deployment.
- The project was syntax-checked locally but has not been deployed or tested on a live server.

## Deploy using a phone
1. Download and unzip this folder.
2. Create a GitHub repository in your mobile browser and upload all files.
3. Create a Render account, select **New + → Blueprint**, and connect the GitHub repository.
4. Set a strong `ADMIN_PASSWORD` when asked, then deploy.
5. Open the generated HTTPS website on your phone, log in, add students, train the model, and test camera attendance.
6. Edit the seven sample times before official use.

Default local password: `ChangeMe123!`. Set a different strong password before deployment.
