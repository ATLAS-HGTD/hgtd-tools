import tkinter
import tkinter.messagebox
import customtkinter

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class CtkGridWrappingLabel(customtkinter.CTkLabel):
    def __init__(self, master=None, height=0, width=0, justify=customtkinter.LEFT, **kwargs):
        super().__init__(master, height=height, width=width, justify=justify, **kwargs)
        self._last_wrap_length: int = 0
        self._resize_after_id = None
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, event):
        new_wrap_length = int(self.winfo_width() / customtkinter.ScalingTracker.get_widget_scaling(self))
        if new_wrap_length == self._last_wrap_length:
            return
        self._last_wrap_length = new_wrap_length

        # Cancel previous
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(100, self._update_wrap_length)

    def _update_wrap_length(self):
        self.configure(wraplength=self._last_wrap_length)
        self._resize_after_id = None

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("HGTD Tools")
        self.geometry(f"{1500}x{900}")

        # configure grid layout (4x4)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame_left = customtkinter.CTkFrame(self, width=140, height=900, corner_radius=0)
        self.sidebar_frame_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame_left.grid_rowconfigure(4, weight=1, minsize=140)
        
        #self.sidebar_frame_right = customtkinter.CTkFrame(self, width=140, height=900, corner_radius=0)
        #self.sidebar_frame_right.grid(row=0, column=3, rowspan=4, sticky="nsew")
        #self.sidebar_frame_right.grid_rowconfigure(4, weight=1)
        
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="HGTD Tools", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))       

        
        #self.version_label = CtkGridWrappingLabel(self.sidebar_frame_right, text="v0.0.1\n\n(April 2025)", font=customtkinter.CTkFont(size=20))
        #self.version_label.configure(wraplength=140)
        #self.version_label.grid(row=0, column=0, padx=20, pady=(20, 10))    

        self.explain_label = customtkinter.CTkLabel(self, text="Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\n\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.\n\n", font=customtkinter.CTkFont(size=16), height=200, wraplength=1000, justify="center")
        self.explain_label.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)    
        
        self.main_frame = customtkinter.CTkFrame(self, width=1000)
        self.main_frame.grid(row=1, column=1, rowspan=1, columnspan=2, padx=20, pady=20, sticky="nsew")
        
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        self.segemented_button = customtkinter.CTkSegmentedButton(self.main_frame, values=["Module Loading", "Detector Assembly (CERN)"],
                                                     command=self.segmented_button_callback,
                                                     width=400, height=30)
        self.segemented_button.set("Module Loading")
        self.segemented_button.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)

        self.combobox_frame = customtkinter.CTkFrame(self.main_frame, width = 400)
        self.combobox_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")


        
        self.combobox_parent_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part Type: Detector Unit")
        self.combobox_parent_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        #self.combobox_parent_T = customtkinter.CTkComboBox(self.combobox_frame,
        #                                            values=["Detector Unit", "Detector"])
        #self.combobox_parent_T.grid(row=0, column=1, padx=20, pady=(10, 10), sticky="nsew")
        #self.combobox_parent_T.set("Detector Unit")


        self.combobox_parent_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part SN")
        self.combobox_parent_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_parent = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Detector Unit", "Detector"])
        self.combobox_parent.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_parent.set("- Select -")



        
        self.combobox_child_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part Type: Module")
        self.combobox_child_T_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        #self.combobox_child_T = customtkinter.CTkComboBox(self.combobox_frame,
        #                                            values=["Module", "Detector Unit"])
        #self.combobox_child_T.grid(row=2, column=1, padx=20, pady=(10, 10), sticky="nsew")
        #self.combobox_child_T.set("Module")
        
        
        self.combobox_child_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part SN")
        self.combobox_child_label.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_child = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Module", "Detector Unit"])
        self.combobox_child.grid(row=3, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_child.set("- Select -")


        self.position_label = customtkinter.CTkLabel(self.combobox_frame, text="Position (derived from canvas interaction)")
        self.position_label.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.VLQ_variable = customtkinter.StringVar(value="- automatic -")
        self.VLQ_entry = customtkinter.CTkEntry(self.combobox_frame, textvariable=self.VLQ_variable, state='disabled')
        self.VLQ_entry.grid(row=4, column=1, padx=20, pady=(10, 10), sticky="nsew")
        

        self.canvas = customtkinter.CTkCanvas(self.main_frame, width = 600, height=600, background='white')
        self.canvas.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        #self.canvas_frame = customtkinter.CTkFrame(self.main_frame, width = 600)
        #self.canvas_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        
        #self.segemented_button.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        
        # create tabview
        '''
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("CTkTabview")
        self.tabview.add("Tab 2")
        self.tabview.add("Tab 3")
        
        self.tabview.tab("CTkTabview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Tab 2").grid_columnconfigure(0, weight=1)

        self.combobox_1 = customtkinter.CTkComboBox(self.tabview.tab("CTkTabview"),
                                                    values=["Value 1", "Value 2", "Value Long....."])
        self.combobox_1.grid(row=1, column=0, padx=20, pady=(10, 10))
        self.combobox_1.set("CTkComboBox")
        

        # ToDo bring this into the frame which contains the form to add partstree relations
        self.main_button_1 = customtkinter.CTkButton(master=self.tabview.tab("CTkTabview"), fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")
        '''

    # https://stackoverflow.com/a/23944658
    def segmented_button_callback(self, value):
        #print("segmented button clicked")
        if value == "Module Loading":
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector Unit")
            self.combobox_child_T_label.configure(text="Child Part Type: Module")
            self.position_label.configure(text="Position (derived from canvas interaction)")
            self.VLQ_variable.set("- automatic -")
            self.VLQ_entry.configure(state="disabled")
        else:
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: Detector Unit")
            self.position_label.configure(text="Position (type by hand)")
            self.VLQ_variable.set("VxLyQz")
            self.VLQ_entry.configure(state="normal")
                
    
    def sidebar_button_event(self):
        print("sidebar_button click")


if __name__ == "__main__":
    app = App()
    app.mainloop()