import cv2
import face_recognition
import numpy as np
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pandas as pd
from fpdf import FPDF

class AttendanceSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.present_students = set()
        
        # Create database directory if not exists
        if not os.path.exists('face_database'):
            os.makedirs('face_database')

        # Load existing faces
        self.load_known_faces()

        # Initialize GUI
        self.root = tk.Tk()
        self.root.title("Smart Attendance System")
        self.root.geometry("800x600")
        self.root.configure(bg="#2C3E50")

        # Style configuration
        style = ttk.Style()
        style.configure("TButton", padding=10, font=('Helvetica', 12))
        style.configure("TLabel", font=('Helvetica', 14), background="#2C3E50", foreground="white")

        # Main buttons
        ttk.Label(self.root, text="Smart Attendance System", 
                 font=('Helvetica', 24, 'bold')).pack(pady=20)
        
        ttk.Button(self.root, text="Register New Student", 
                  command=self.register_student).pack(pady=10)
        ttk.Button(self.root, text="Take Attendance", 
                  command=self.take_attendance).pack(pady=10)
        ttk.Button(self.root, text="Generate Report", 
                  command=self.generate_report).pack(pady=10)

        # Add status labels
        self.status_label = ttk.Label(self.root, text="System Status: Ready", 
                                font=('Helvetica', 12), foreground="#2ECC71")
        self.status_label.pack(pady=10)
    
        # Add count label
        self.count_label = ttk.Label(self.root, text="Students Present: 0/0", 
                               font=('Helvetica', 12), foreground="#3498DB")
        self.count_label.pack(pady=5)

    def load_known_faces(self):
        for filename in os.listdir('face_database'):
            if filename.endswith('.jpg'):
                image_path = os.path.join('face_database', filename)
                image = face_recognition.load_image_file(image_path)
                encoding = face_recognition.face_encodings(image)[0]
                self.known_face_encodings.append(encoding)
                self.known_face_names.append(filename.split('.')[0])

    def register_student(self):
        self.reg_window = tk.Toplevel(self.root)
        self.reg_window.title("Register New Student")
        self.reg_window.geometry("600x500")
        self.reg_window.configure(bg="#2C3E50")

        # Add registration status label
        self.reg_status_label = ttk.Label(self.reg_window, 
                                     text="Ready to capture", 
                                     font=('Helvetica', 12),
                                     foreground="#2ECC71")
        self.reg_status_label.pack(pady=5)

        ttk.Label(self.reg_window, text="Enter Student Name:").pack(pady=10)
        self.name_entry = ttk.Entry(self.reg_window, font=('Helvetica', 12))
        self.name_entry.pack(pady=5)

        self.reg_camera_label = ttk.Label(self.reg_window)
        self.reg_camera_label.pack(pady=10)

        self.reg_status_label = ttk.Label(self.reg_window, text="", font=('Helvetica', 12))
        self.reg_status_label.pack(pady=5)

        self.capture = cv2.VideoCapture(0)
        self.update_registration_feed()

        ttk.Button(self.reg_window, text="Capture", 
                  command=self.capture_face).pack(pady=10)

    def update_registration_feed(self):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (400, 300))
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
            self.reg_camera_label.configure(image=photo)
            self.reg_camera_label.image = photo
        self.reg_window.after(10, self.update_registration_feed)

    def capture_face(self):
        ret, frame = self.capture.read()
        if ret:
            name = self.name_entry.get().strip()
            if name:
                # Update status
                self.reg_status_label.config(text="Processing face...", foreground="#F1C40F")
                
                # Detect if there is a face in the frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    self.reg_status_label.config(text="No face detected! Please try again.", 
                                               foreground="#E74C3C")
                    return
                
                try:
                    # Save the image
                    image_path = f'face_database/{name}.jpg'
                    cv2.imwrite(image_path, frame)
                    
                    # Verify and process
                    if not os.path.exists(image_path):
                        raise Exception("Failed to save image")
                    
                    image = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(image)
                    
                    if not encodings:
                        os.remove(image_path)
                        raise Exception("Could not encode face in image")
                    
                    # Add to known faces
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_names.append(name)
                    
                    # Update status
                    self.reg_status_label.config(text=f"✅ {name} registered successfully!", 
                                               foreground="#2ECC71")
                    self.status_label.config(text=f"System Status: Added {name}")
                    
                    # Close after 2 seconds
                    self.reg_window.after(2000, self.reg_window.destroy)
                    self.capture.release()
                    cv2.destroyAllWindows()
                    
                except Exception as e:
                    self.reg_status_label.config(text=f"❌ Error: {str(e)}", 
                                               foreground="#E74C3C")
                    if os.path.exists(image_path):
                        os.remove(image_path)
            else:
                self.reg_status_label.config(text="Please enter a name!", 
                                           foreground="#E74C3C")

    def take_attendance(self):
        self.attend_window = tk.Toplevel(self.root)
        self.attend_window.title("Take Attendance")
        self.attend_window.geometry("800x600")
        self.attend_window.configure(bg="#2C3E50")

        self.attend_camera_label = ttk.Label(self.attend_window)
        self.attend_camera_label.pack(pady=10)

        self.capture = cv2.VideoCapture(0)
        self.update_attendance_feed()

        ttk.Button(self.attend_window, text="Complete Attendance", 
                  command=self.complete_attendance).pack(pady=10)

    def update_attendance_feed(self):
        ret, frame = self.capture.read()
        if ret:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        
                        # Update attendance and UI
                        if name not in self.present_students:
                            self.present_students.add(name)
                            self.status_label.config(
                                text=f"✅ {name} marked present!", 
                                foreground="#2ECC71"
                            )
                            # Update count
                            self.count_label.config(
                                text=f"Students Present: {len(self.present_students)}/{len(self.known_face_names)}"
                            )
                        
                        # Draw rectangle and name
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, f"{name} (Present)", (left, top - 10), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Display the frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 480))
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
            self.attend_camera_label.configure(image=photo)
            self.attend_camera_label.image = photo

            # Update window title with count
            self.attend_window.title(f"Taking Attendance - {len(self.present_students)} Present")

        self.attend_window.after(10, self.update_attendance_feed)

    def complete_attendance(self):
        self.capture.release()
        self.attend_window.destroy()
        self.generate_report()

    def generate_report(self):
        date = datetime.now().strftime("%Y-%m-%d")
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16)
        pdf.cell(200, 10, txt=f"Attendance Report - {date}", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        
        for idx, student in enumerate(sorted(self.present_students), 1):
            pdf.cell(200, 10, txt=f"{idx}. {student}", ln=1, align='L')

        filename = f"attendance_report_{date}.pdf"
        pdf.output(filename)
        messagebox.showinfo("Success", f"Report generated: {filename}")
        self.present_students.clear()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AttendanceSystem()
    app.run()