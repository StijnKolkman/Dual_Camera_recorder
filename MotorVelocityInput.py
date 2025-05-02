import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import include.Motor as mtr

class MotorVelocityInput:

    def __init__(self, maximumFrequency, relativeIncrease, motorConnected=True, motorNode=1, motorUSB=0, motorAcceleration=8000):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.geometry("400x400")
        self.root.title("Bar Plot Example")
        self.root.update()

        self.freqDisplay = ctk.CTkTextbox(master=self.root,
                                          height= self.root.winfo_height()*0.95,
                                          width= self.root.winfo_width()*0.45,
                                          font= ("Helvetica", 30))
        self.freqDisplay.tag_config("center", justify="center")
        self.freqDisplay.place(relx=0.025, rely=0.025)

        self.barDisplay = ctk.CTkFrame(master=self.root,
                                       height=self.root.winfo_height()*0.95,
                                       width= self.root.winfo_width()*0.45)
        self.barDisplay.place(relx=0.525,rely=0.025)

        # Global variable to hold the bar value
        self.rpmFreq = 0
        self.rpmDirection = 1
        self.maximumFrequency = maximumFrequency
        self.relativeIncrease = relativeIncrease
        self.motorConnected = motorConnected

        if self.motorConnected:
            self.motor = mtr.Motor(motorNode,motorUSB)
            self.motor.OpenCommunication()
            if self.motor.keyhandle != 0:
                self.motor.EnableMotor()
                self.motor.SetVelocityProfile(motorAcceleration,motorAcceleration)

        # Matplotlib figure and axis
        fig, self.ax = plt.subplots()
        self.bar = self.ax.bar(["Bar"], [self.rpmFreq])
        self.ax.set_ylim([0, self.maximumFrequency+1])
        self.bar[0].set_color('blue')

        # Embedding the matplotlib figure into customtkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.barDisplay)  # Create canvas for figure
        self.canvas.get_tk_widget().place(relwidth=1, relheight=1)  # Pack inside the frame
        self.canvas.draw()  # Draw initial plot
        self.setBindings()

        # Give closing commands
        self.root.protocol("WM_DELETE_WINDOW", self.onClosing)

        # Initiate figure
        self.root.mainloop()

    def update_bar_plot(self):
        # Update heights
        self.bar[0].set_height(self.rpmFreq)
        # Clear the textbox (optional if you want to replace old content)
        self.freqDisplay.delete("1.0", "end")
        # Insert the value of self.rpmFreq
        self.freqDisplay.insert("1.0", "\n"+str(round(self.rpmDirection*self.rpmFreq,3)),"center")

        # Update color from direction
        colorMap = {
            1: 'blue',
            -1: 'red'
        }
        self.bar[0].set_color(colorMap.get(self.rpmDirection, 'black')) # Default black color
        self.canvas.draw()

    def setBindings(self):
        Bindings = {
            '<Up>': self.upKey,
            '<Down>': self.downKey,
            '<Left>': self.leftKey,
            '<Right>': self.rightKey,
            '1': lambda x: self.setRPMbyKey(1),
            '2': lambda x: self.setRPMbyKey(2),
            '3': lambda x: self.setRPMbyKey(3),
            '4': lambda x: self.setRPMbyKey(4),
            '5': lambda x: self.setRPMbyKey(5),
            '6': lambda x: self.setRPMbyKey(6),
            '7': lambda x: self.setRPMbyKey(7),
            '8': lambda x: self.setRPMbyKey(8),
            '9': lambda x: self.setRPMbyKey(9),
            '0': lambda x: self.setRPMbyKey(10),
            '<Delete>': lambda x: self.setRPM(0),
            ',': lambda x: self.setDirection(-1),
            '.': lambda x: self.setDirection(1),
            '<space>': lambda x: self.setDirection(-1 * self.rpmDirection)
        }
        for key, function in Bindings.items():
            self.root.bind(key, function)
    # Arrow key event handlers
    def upKey(self,event):
        if self.relativeIncrease:
            self.setRPM(self.rpmFreq + 0.01*self.maximumFrequency) # Increase RPM frequency with 1% of max
        else:
            self.setRPM(self.rpmFreq + 0.1) # Increase RPM frequency with 0.1 Hz
    def downKey(self,event):
        if self.relativeIncrease:
            self.setRPM(self.rpmFreq - 0.01*self.maximumFrequency) # Decrease RPM frequency with 1% of max
        else:
            self.setRPM(self.rpmFreq - 0.1) # Decrease RPM frequency with 0.1 Hz
        
    def leftKey(self,event):
        if self.relativeIncrease:
            self.setRPM(self.rpmFreq - 0.05*self.maximumFrequency) # Decrease RPM frequency with 5% of max
        else:
            self.setRPM(self.rpmFreq - 0.5) # Decrease RPM frequency with 0.5 Hz
        
    def rightKey(self,event):
        if self.relativeIncrease:
            self.setRPM(min(self.maximumFrequency,self.rpmFreq + 0.05*self.maximumFrequency)) # Increase RPM frequency with 5% of max
        else:
            self.setRPM(min(self.maximumFrequency,self.rpmFreq + 0.5)) # Increase RPM frequency with 0.5 Hz
        

    # Number key event handlers
    def setRPMbyKey(self, key):
        if self.relativeIncrease:
            self.setRPM(0.1*key*self.maximumFrequency)
        else:
            self.setRPM(key)
    
    def setRPM(self, rpm):
        # Limit rpm between 0 and maximum
        rpm = min(self.maximumFrequency, max(0, rpm))
        self.rpmFreq = rpm
        self.update_bar_plot()
        if self.motorConnected:
            self.motor.RunSetVelocity(int((26.0/7.0)*60.0*self.rpmFreq*self.rpmDirection))

    def setDirection(self, direction):
        self.rpmDirection = direction
        self.update_bar_plot()
        if self.motorConnected:
            self.motor.RunSetVelocity(int((26.0/7.0)*60.0*self.rpmFreq*self.rpmDirection))

    # Miscellaneous motor key handlers

    # Function to terminate running program when closing the figure
    def onClosing(self):
        if self.motorConnected:
            self.motor.DisableMotor() 
            self.motor.CloseCommunication()
        self.root.quit()

if __name__ == "__main__":        
    CTK_Window = MotorVelocityInput(10,True,True)
    