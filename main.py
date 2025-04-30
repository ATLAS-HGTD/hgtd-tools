import customtkinter
import api
import data
import util
from pprint import pprint
import time
import threading

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def load_relevant_parts(partKoP_shortname, onlyNonDeleted = True):
    KoP_ID = data.KoPID_from_partKoPName[partKoP_shortname]
    these_parts = api.fetch_information(f'/partslistbykop/{KoP_ID}/')
    these_parts = [tP for tP in these_parts if tP['is_record_deleted'] == 'F']
    return these_parts

def grab_relevant_SNs_and_partIDs(partsList):
    these_SNs_and_partIDs = util.getSortedListOfListsByNthColumn([[pL['serial_number'],pL['part_id']] for pL in partsList], 0)
    return these_SNs_and_partIDs
    
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("HGTD Tools")
        self.geometry(f"{1500}x{900}")

        # configure grid layout
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame_left = customtkinter.CTkFrame(self, width=140, height=900, corner_radius=0)
        self.sidebar_frame_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame_left.grid_rowconfigure(4, weight=1, minsize=140)
        
        # fill sidebar
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="HGTD Tools", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.progress_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="API Request Status")
        self.progress_label.grid(row=1, column=0, padx=20, pady=10)
        self.progressbar = customtkinter.CTkProgressBar(self.sidebar_frame_left, orientation="horizontal")
        self.progressbar.grid(row=2, column=0, padx=20, pady=10)
        self.progressbar.set(1)

        # work in main widget (column w.r.t. root >= 1)
        self.explain_label = customtkinter.CTkLabel(self, text="Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\n\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.\n\n", font=customtkinter.CTkFont(size=16), height=200, wraplength=1000, justify="center")
        self.explain_label.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)    

        # create main frame with widgets
        self.main_frame = customtkinter.CTkFrame(self, width=1200)
        self.main_frame.grid(row=1, column=1, rowspan=1, columnspan=2, padx=20, pady=20, sticky="nsew")
        
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # button to select use case of the tool
        self.segemented_button = customtkinter.CTkSegmentedButton(self.main_frame, values=["Module Loading", "Detector Assembly (CERN)"],
                                                     command=self.segmented_button_callback,
                                                     width=400, height=30)
        self.segemented_button.set("Module Loading")
        self.segemented_button.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)

        # left sub widget: form
        self.combobox_frame = customtkinter.CTkFrame(self.main_frame, width = 400)
        self.combobox_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        self.combobox_parent_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part Type: Detector Unit")
        self.combobox_parent_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), sticky="nsew") 

        self.combobox_parent_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part SN")
        self.combobox_parent_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_parent = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Detector Unit", "Detector"])
        self.combobox_parent.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_parent.set("- Select -")

        self.combobox_child_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part Type: Module")
        self.combobox_child_T_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew") 
                
        self.combobox_child_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part SN")
        self.combobox_child_label.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_child = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Module", "Detector Unit"])
        self.combobox_child.grid(row=3, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_child.set("- Select -")

        self.position_label = customtkinter.CTkLabel(self.combobox_frame, text="Position (derived from canvas interaction)")
        self.position_label.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")
        
        self.position_variable = customtkinter.StringVar(value="- automatic -")
        self.position_entry = customtkinter.CTkEntry(self.combobox_frame, textvariable=self.position_variable, state='disabled')
        self.position_entry.grid(row=4, column=1, padx=20, pady=(10, 10), sticky="nsew")

        self.add_button = customtkinter.CTkButton(self.combobox_frame, text="ADD PARTS TREE",
                                                   command=self.add_button_event)
        self.add_button.grid(row=5, column=1, padx=20, pady=(10, 10))

        # right sub widget: canvas containing DUs to click on
        self.canvas = customtkinter.CTkCanvas(self.main_frame, width = 600, height=600, background='white')
        self.canvas.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        self.info_label = customtkinter.CTkLabel(self.main_frame, text=" ", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.info_label.grid(row=2, column=0, padx=20, pady=20, columnspan=2)

        
        # First startup of program defaults to Module Loading
        self.possible_parents = load_relevant_parts('Detector Unit')
        self.possible_children = load_relevant_parts('Module')
        
        self.possible_parents_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_parents)
        self.possible_children_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_children)
        self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
        self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
        self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
        self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
        self.combobox_parent.configure(values=self.possible_parents_SNs)
        self.combobox_child.configure(values=self.possible_children_SNs)
        
    def load_p_c(self, p, c):
        self.possible_parents = load_relevant_parts(p)
        self.possible_children = load_relevant_parts(c)

    def update_progressbar(self, thread):
        if thread.is_alive():
            # update progressbar
            self.progressbar.step()
            self.after(250, self.update_progressbar, thread)
        else:
            self.progressbar.set(1)
        
    # https://stackoverflow.com/a/23944658
    def segmented_button_callback(self, value):
        self.progressbar.set(0)
        #print("segmented button clicked")
        if value == "Module Loading":
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector Unit")
            self.combobox_child_T_label.configure(text="Child Part Type: Module")
            self.position_label.configure(text="Position (derived from canvas interaction)")
            self.position_variable.set("- automatic -")
            self.position_entry.configure(state="disabled")
            
            self.loading_wheel = threading.Thread(target=self.load_p_c, args=('Detector Unit','Module'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
            
        else:
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: Detector Unit")
            self.position_label.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")

            self.loading_wheel = threading.Thread(target=self.load_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        
        self.possible_parents_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_parents)
        self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
        self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
        self.possible_children_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_children)
        self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
        self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]

        self.combobox_parent.configure(values=self.possible_parents_SNs)
        self.combobox_child.configure(values=self.possible_children_SNs)

    
    def add_button_event(self):
        chi = self.combobox_child.get()
        par = self.combobox_parent.get()
        pos = self.position_entry.get()
        if chi == '- Select -' or par == '- Select -' or pos == '- automatic -' or pos == 'VxLyQz':
            # perhaps add a popup window in the future
            info_text = 'Warning: Select a child & parent from the respective lists and a position to proceed.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.info_label.configure(text=' ')
            part_tree = {
                'position': pos,
                'is_record_deleted': 'F',
                'part': self.possible_children_partIDs[self.possible_children_SNs.index(chi)],
                'part_parent': self.possible_parents_partIDs[self.possible_parents_SNs.index(par)],
            }
            
            api.post_information('/partstreelist', part_tree)
        
if __name__ == "__main__":
    app = App()
    app.mainloop()