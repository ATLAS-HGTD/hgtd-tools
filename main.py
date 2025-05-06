import customtkinter
import requests
import threading
import time
import tkinter

import api
import data
import util

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

wrapped_text = util.CustomTextWrapper(width=90)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("HGTD Tools")
        self.geometry(f"{1500}x{1000}")
        icon = tkinter.PhotoImage(file="windowIcon.png")
        self.iconphoto(True,icon)

        # configure grid layout
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0,1), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame_left = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame_left.grid_columnconfigure(0, weight=1)
        self.sidebar_frame_left.grid_rowconfigure(4, weight=1)

        # fill sidebar
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="HGTD Tools", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10), columnspan=2)
        self.credits_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="v1.0.0dev - May 2025\nAnnika Stein (JGU Mainz)")
        self.credits_label.grid(row=1, column=0, padx=20, pady=10, columnspan=2)

        self.progress_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="API Request Status")
        self.progress_label.grid(row=2, column=0, padx=20, pady=10, columnspan=2)
        self.progressbar = customtkinter.CTkProgressBar(self.sidebar_frame_left, orientation="horizontal", progress_color="#007711")
        self.progressbar.grid(row=3, column=0, padx=20, pady=10, columnspan=2)
        self.progressbar.set(1)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=10, pady=10)
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame_left, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=5, column=1, padx=10, pady=10)
        self.appearance_mode_optionemenu.set("System")


        # work in main widget (column w.r.t. root >= 1)
        self.explain_frame = customtkinter.CTkFrame(self)#CTkXYFrame(self)
        self.explain_frame.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)

        self.textbox = customtkinter.CTkTextbox(master=self.explain_frame, width=400, wrap='word')
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert("0.0", "Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\n\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.")
        self.textbox.configure(state='disabled')

        # create main frame with widgets
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=1, column=1, rowspan=1, columnspan=2, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # button to select use case of the tool
        self.segmented_button = customtkinter.CTkSegmentedButton(self.main_frame,
                                                                 values=["Module Loading", "Detector Assembly (CERN)"],
                                                                 command=self.button_mode_event_click)
        self.segmented_button.set("Module Loading")
        self.segmented_button.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="nsew")

        # left sub widget: form
        self.combobox_frame = customtkinter.CTkFrame(self.main_frame, width = 600)
        self.combobox_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.combobox_frame.grid_columnconfigure((0,1), weight=1)

        self.combobox_parent_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part Type: Detector Unit")
        self.combobox_parent_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew")

        self.combobox_parent_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part SN")
        self.combobox_parent_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_parent = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Detector Unit", "Detector"],
                                                    command=self.combobox_p_c_event_select
                                                        )
        self.combobox_parent.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_parent.set("- Select -")
        self.inspect_parent_button = customtkinter.CTkButton(self.combobox_frame, text="INSPECT PARENT",
                                                   command=self.button_inspect_parent_event_click)
        self.inspect_parent_button.grid(row=2, column=1, padx=20, pady=(10, 10))

        self.combobox_child_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part Type: Module")
        self.combobox_child_T_label.grid(row=3, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew")

        self.combobox_child_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part SN")
        self.combobox_child_label.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_child = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Module", "Detector Unit"],
                                                    command=self.combobox_p_c_event_select)
        self.combobox_child.grid(row=4, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_child.set("- Select -")
        self.inspect_child_button = customtkinter.CTkButton(self.combobox_frame, text="INSPECT CHILD",
                                                   command=self.button_inspect_child_event_click)
        self.inspect_child_button.grid(row=5, column=1, padx=20, pady=(10, 10))

        self.position_label = customtkinter.CTkLabel(self.combobox_frame, text="Position (derived from canvas interaction)")
        self.position_label.grid(row=6, column=0, padx=20, pady=(20, 10), sticky="nsew")

        self.position_variable = customtkinter.StringVar(value="- automatic -")
        self.position_entry = customtkinter.CTkEntry(self.combobox_frame, textvariable=self.position_variable, state='disabled')
        self.position_entry.grid(row=6, column=1, padx=20, pady=(20, 10), sticky="nsew")

        self.add_button = customtkinter.CTkButton(self.combobox_frame, text="ADD PARTS TREE",
                                                   command=self.button_add_event_click)
        self.add_button.grid(row=7, column=1, padx=20, pady=(20, 10))


        # right sub widget: canvas containing DUs to click on
        self.canvas_label = customtkinter.CTkLabel(self.main_frame, text="Interactive canvas: accepting user click")
        self.canvas_label.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="nsew")

        self.canvas = customtkinter.CTkCanvas(self.main_frame, width = 500, height = 700, background='white')
        self.canvas.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.canvas.bind('<Button-1>', self.canvas_event_click)
        self.displayedDUtype = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []


        # footer: info for user (e.g. Warning, Error)
        self.info_label = customtkinter.CTkLabel(self.main_frame, text=" ", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.info_label.grid(row=2, column=0, padx=20, pady=20, columnspan=2)


        # First startup of program: default values
        self.api_status = 1
        self.last_responseText = ''
        self.slots = None
        self.partstree = None

        # Get first parents and children (Module Loading)
        try:
            self.possible_parents, self.last_responseText = util.get_relevant_parts('Detector Unit')
            self.possible_children, self.last_responseText = util.get_relevant_parts('Module')
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")
            self.possible_parents_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.combobox_parent.configure(values=self.possible_parents_SNs)
            self.combobox_child.configure(values=self.possible_children_SNs)

    def button_add_event_click(self, debug = False):
        chi = self.combobox_child.get()
        par = self.combobox_parent.get()
        pos = self.position_entry.get()
        if chi == '- Select -' or par == '- Select -' or pos == '- automatic -' or pos == 'VxLyQz':
            info_text = 'Warning: Select a child & parent from the respective lists and a position to proceed.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.info_label.configure(text=' ')
            chi_partID = self.possible_children_partIDs[self.possible_children_SNs.index(chi)]
            par_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(par)]
            part_tree = {
                'position': pos,
                'is_record_deleted': 'F',
                'part': chi_partID,
                'part_parent': par_partID,
            }
            allowed_VLQ = False
            occupied_VLQ = False
            confirmed = pos
            try:
                if self.segmented_button.get() == 'Module Loading':
                    self.last_responseText = api.post_information('/partstreelist', part_tree)
                    
                    self.displayedDUtype = "None"
                    self.this_DU_relations_MODULE = []
                    self.this_MODULE_relations_DU = []
                    self.this_MODULE_relations_SLOT = []
                    self.possible_parents = []
                    self.possible_children = []
                    self.slots = None
                    self.partstree = None
                    
                    self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(chi, par))
                    self.loading_wheel.start()
                    self.update_progressbar(self.loading_wheel)
                elif self.segmented_button.get() == 'Detector Assembly (CERN)':
                    attribute_Vessel = pos.split('V').pop().split('L')[0]
                    if attribute_Vessel not in ['1', '2', 'M', 'D']:
                        info_text = wrapped_text.fill(f'Error: You can not load to this vessel.\nVessel attribute only accepts 1, 2, M, or D, but you selected {attribute_Vessel}!')
                        print(f'>>> {info_text}')
                        self.info_label.configure(text=info_text)
                    else:
                        attribute_Layer = pos.split('L').pop().split('Q')[0]
                        if attribute_Layer not in ['0', '1', '2', '3']:
                            info_text = wrapped_text.fill(f'Error: You can not load to this layer.\nLayer attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Layer}!')
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            if attribute_Layer == '0' or attribute_Layer == '3':
                                allowed_type = 'F'
                                not_allowed_type = 'B'
                            else:#elif attribute_Layer == '1' or attribute_Layer == '2':
                                allowed_type = 'B'
                                not_allowed_type = 'F'
                            if self.displayedDUtype[0] == not_allowed_type:
                                info_text = wrapped_text.fill(f'Error: You can not load this DU to this layer.\nLayer {attribute_Layer} only accepts {allowed_type} DUs, but you selected a {self.displayedDUtype[0]} DU!')
                                print(f'>>> {info_text}')
                                self.info_label.configure(text=info_text)
                            else:
                                attribute_Quadrant = pos.split('Q').pop()
                                if attribute_Quadrant not in ['0', '1', '2', '3']:
                                    info_text = wrapped_text.fill(f'Error: You can not load to this quadrant.\nQuadrant attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Quadrant}!')
                                    print(f'>>> {info_text}')
                                    self.info_label.configure(text=info_text)
                                else:
                                    allowed_VLQ = True
                                    children_of_targetDetector, self.last_responseText = util.get_children(par_partID)
                                    DU_already_occupying_target_position = ''
                                    Det_DU_relation_to_delete = ''
                                    matching_relation = []
                                    for c in children_of_targetDetector:
                                        # position of Det child is the same as the desired one, and DU type of desired DU is same as the one that already occupies the spot:
                                        if str(c['position']) == pos and self.displayedDUtype in c['part']['serial_number']:
                                            occupied_VLQ = True
                                            DU_already_occupying_target_position = c['part']['serial_number']
                                            Det_DU_relation_to_delete = c['record_id']
                                            matching_relation = c
                                            break

                                    if occupied_VLQ:
                                        confirmed = ''
                                        dialog = customtkinter.CTkInputDialog(text=f"This Vessel Layer Quadrant is already occupied by the DU {DU_already_occupying_target_position}.\n" +
                                            "Confirm by typing the desired Vessel Layer Quadrant (VxLyQz) again to overwrite it with your selected DU:", title="Confirm dialog")
                                        confirmed = dialog.get_input()
                                        if debug:
                                            print("Typed in slot from confirm dialog:", confirmed)
                                        if confirmed == pos:
                                            # DELETION OF PREVIOUS STUFF

                                            # delete Det -> DU relation for the DU that already occupies that VLQ
                                            self.last_responseText = api.delete_information(f'/partstreedelete/{Det_DU_relation_to_delete}/')
                                            # get children modules of the DU that previously occupied the VLQ
                                            affected_previous_modules, self.last_responseText = util.get_children(matching_relation['part']['part_id'])
                                            # the parent slots of modules of the DU that previously occupied the VLQ
                                            for a in affected_previous_modules:
                                                affected_parents_of_children, self.last_responseText = util.get_parents(a['part']['part_id'])
                                                for p in affected_parents_of_children:
                                                    if debug:
                                                        print(str(p['part_parent']['kind_of_part']['kind_of_part_id']))
                                                    if str(p['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                                                        # delete those Slot -> Mod relations
                                                        if debug:
                                                            print('Delete Slot -> Module relation', p)
                                                        self.last_responseText = api.delete_information(f'/partstreedelete/{p['record_id']}/')

                                            # POSTING NEW STUFF

                                            # place new DU at this position by creating a new Det -> DU relation
                                            self.last_responseText = api.post_information('/partstreelist', part_tree)
                                            self.canvas.itemconfig(self.duAlreadyPlacedText, text=f'Now placed at:\n{pos}')
                                    else:
                                        self.last_responseText = api.post_information('/partstreelist', part_tree)
                                        self.canvas.itemconfig(self.duAlreadyPlacedText, text=f'Now placed at:\n{pos}')

            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                if self.segmented_button.get() == 'Detector Assembly (CERN)' and allowed_VLQ and ((occupied_VLQ and confirmed == pos) or not occupied_VLQ):
                    # find all existing relations between this DU and its Modules, those are propagated to create new Slot -> Module relations
                    self.loading_wheel_A = threading.Thread(target=self.fetch_and_write_module_slots, args=(attribute_Vessel, attribute_Layer, attribute_Quadrant))
                    self.loading_wheel_A.start()
                    self.update_progressbar(self.loading_wheel_A)

    def button_inspect_child_event_click(self):
        childSNIn = self.combobox_child.get()
        if childSNIn != '- Select -':
            chi_partID = self.possible_children_partIDs[self.possible_children_SNs.index(childSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{chi_partID}')

    def button_inspect_parent_event_click(self):
        parentSNIn = self.combobox_parent.get()
        if parentSNIn != '- Select -':
            par_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(parentSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{par_partID}')

    # https://stackoverflow.com/a/23944658
    def button_mode_event_click(self, value):
        self.displayedDUtype = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.possible_parents = []
        self.possible_children = []
        self.slots = None
        self.partstree = None

        self.progressbar.set(0)
        self.info_label.configure(text=' ')
        self.canvas.delete("all")
        if value == "Module Loading":
            self.canvas_label.configure(text='Interactive canvas: accepting user click')
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector Unit")
            self.combobox_child_T_label.configure(text="Child Part Type: Module")
            self.position_label.configure(text="Position (derived from canvas interaction)")
            self.position_variable.set("- automatic -")
            self.position_entry.configure(state="disabled")
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector Unit','Module'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        else:
            self.canvas_label.configure(text='Static canvas: served from database')
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: Detector Unit")
            self.position_label.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def canvas_event_click(self, event, debug = False):
        if self.segmented_button.get() == 'Module Loading':
            if self.displayedDUtype != 'None':
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                alreadyConnectedModules = self.this_DU_relations_MODULE # list of relations, as in partstree
                if debug:
                    print(alreadyConnectedModules)
                alreadyUsedSlots = [entry['position'] for entry in alreadyConnectedModules]

                alreadyConnectedDUsForModule = self.this_MODULE_relations_DU
                alreadyConnectedSLOTsForModule = self.this_MODULE_relations_SLOT

                if len(alreadyConnectedDUsForModule) + len(alreadyConnectedSLOTsForModule) > 0:
                    self.position_variable.set("- automatic -")
                    info_text = 'Warning: This module is already connected to some parent.\nSelect a different one, or disconnect the parents of this module by inspecting the Module.\nThere you can delete existing relations with the red trash button.'
                    print(f'>>> {info_text}')
                    if debug:
                        print('Existing connections to the following DU(s):',[DU['part_parent']['serial_number'] for DU in alreadyConnectedDUsForModule])
                        print('Existing connections to the following Slot(s):',[SLOT['part_parent']['serial_number'] for SLOT in alreadyConnectedSLOTsForModule])
                    self.info_label.configure(text=info_text)
                else:
                    mouseInSomeMod = False
                    mouseX = self.canvas.canvasx(event.x)
                    mouseY = self.canvas.canvasy(event.y)
                    for slot in arrayOfModulesInDU:
                        if util.isInSlot(slot, mouseX, mouseY):
                            mouseInSomeMod = True
                            self.position_variable.set(slot['slot'])
                            notAllowedSlot = False
                            if slot['slot'] in alreadyUsedSlots:
                                notAllowedSlot = True
                                self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_AlreadyLoadedSlot)
                            else:
                                self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_ActiveSlot)
                        else:
                            if slot['slot'] in alreadyUsedSlots:
                                self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_AlreadyLoadedSlot)
                            else:
                                self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_Slot)
                    if not mouseInSomeMod:
                        self.position_variable.set("- automatic -")
                        info_text = 'Warning: Place mouse in some module slot.'
                        print(f'>>> {info_text}')
                        self.info_label.configure(text=info_text)
                    else:
                        if notAllowedSlot:
                            self.position_variable.set("- automatic -")
                            info_text = 'Warning: This slot is already in use.\nSelect a different one, or disconnect the already loaded module by inspecting the DU.\nThere you can delete existing relations with the red trash button.'
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            self.info_label.configure(text=' ')
        else:
            pass

    # https://stackoverflow.com/a/44100075
    def canvas_place_rounded_rectangle(self, x1, y1, width, height, radius=25, **kwargs):
        x2 = x1 + width
        y2 = y1 + height

        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]

        self.canvas.create_polygon(points, **kwargs, smooth=True)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def combobox_p_c_event_select(self, something):
        self.displayedDUtype = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.possible_parents = []
        self.possible_children = []
        self.slots = None
        self.partstree = None
        
        parentSNIn = self.combobox_parent.get()
        childSNIn = self.combobox_child.get()
        if self.segmented_button.get() == 'Module Loading':
            parentNameIn = 'Detector Unit'
            childNameIn = 'Module'
            self.canvas.delete("all")
            if parentSNIn != '- Select -':
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
        else:
            parentNameIn = 'Detector'
            childNameIn = 'Detector Unit'
            self.canvas.delete("all")
            if childSNIn != '- Select -':
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)

    def delete_old_and_post_new_slots_for_loaded_modules(self, V, L, Q):
        for entry in self.this_DU_relations_MODULE:
            try:
                parents_of_child_module, self.responseText = util.get_parents(entry['part']['part_id'])
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Parents could not be loaded from ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                for r in parents_of_child_module:
                    if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                        try:
                            self.last_responseText = api.delete_information(f'/partstreedelete/{r['record_id']}/')
                        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                            self.last_responseText = str(e)
                        except ValueError as e:
                            self.last_responseText = str(e)

                        if self.last_responseText[:2] != '20':
                            self.api_status = 0
                            self.progressbar.configure(progress_color="#ff0000")
                            info_text = wrapped_text.fill(f'Error: Record could not be deleted from ProdDB API.\n{self.last_responseText}')
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            self.api_status = 1
                            self.progressbar.configure(progress_color="#007711")
                if self.api_status == 1:
                    attribute_SU_r = entry['position'].split('R').pop().split('M')[0]
                    attribute_SU_m = entry['position'].split('M').pop()
                    for sl in self.slots:
                        # ToDo: replace the ['part_serial_number'][1] with ['Vessel'] in the (a bit far?) future
                        # (requires re-upload of good slot table, only comes after fixing flex tail lengths
                        # -> this should include replacement of Vessel C/A to 1/2 for attributes!!!
                        if (sl['part_serial_number'][1] == V \
                            and sl['Layer'] == L \
                            and sl['Quadrant'] == Q \
                            and sl['SU_type'] == self.displayedDUtype \
                            and sl['SU_Row'] == attribute_SU_r \
                            and sl['SU_Module'] == attribute_SU_m):
                            # found a slot :-)
                            part_tree = {
                                'position': '',
                                'is_record_deleted': 'F',
                                'part': entry['part']['part_id'],
                                'part_parent': sl['part_id'],
                            }
                            try:
                                self.last_responseText = api.post_information('/partstreelist', part_tree)
                            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                                self.last_responseText = str(e)
                            except ValueError as e:
                                self.last_responseText = str(e)

                            if self.last_responseText[:2] != '20':
                                self.api_status = 0
                                self.progressbar.configure(progress_color="#ff0000")
                                info_text = wrapped_text.fill(f'Error: Parent / Child relation could not be patched to ProdDB API.\n{self.last_responseText}')
                                print(f'>>> {info_text}')
                                self.info_label.configure(text=info_text)
                            else:
                                self.api_status = 1
                                self.progressbar.configure(progress_color="#007711")

    def fetch_and_write_module_slots(self, attribute_Vessel, attribute_Layer, attribute_Quadrant, debug = False):
        if self.api_status == 1:
            if debug:
                if len(self.this_DU_relations_MODULE) == 0:
                    info_text = wrapped_text.fill(f'Warning: There is no relation to a module for this DU.')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
            self.fetch_slots()
            self.delete_old_and_post_new_slots_for_loaded_modules(attribute_Vessel, attribute_Layer, attribute_Quadrant)

    def fetch_loaded_DU_and_display(self, childSNIn, parentSNIn, debug = False):
        if self.segmented_button.get() == 'Module Loading':
            DU_SN = parentSNIn
            parentDU_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(DU_SN)]
            if childSNIn != '- Select -':
                childModule_partID = self.possible_children_partIDs[self.possible_children_SNs.index(childSNIn)]
                # fetch possibly existing parents of module to make sure we don't load it again somewhere else
                try:
                    self.module_parents, self.last_responseText = util.get_parents(childModule_partID)
                except(requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    self.module_parents = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.module_parents = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != '200':
                    self.api_status = 0
                    self.progressbar.configure(progress_color="#ff0000")
                    info_text = wrapped_text.fill(f'Error: Module relations could not be loaded from ProdDB API.\n{self.last_responseText}')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    self.this_MODULE_relations_DU = []
                    self.this_MODULE_relations_SLOT = []
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color="#007711")
                    for r in self.module_parents:
                        if debug:
                            print(r)
                        if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Detector Unit']):
                            self.this_MODULE_relations_DU.append(r)
                        if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                            self.this_MODULE_relations_SLOT.append(r)
        else:
            DU_SN = childSNIn
            parentDU_partID = self.possible_children_partIDs[self.possible_children_SNs.index(DU_SN)]

        self.duAlreadyPlacedText = self.canvas.create_text(380, 525, text=f'', anchor='nw', fill=data.fillColor_SU_Text)

        for key in data.allDUs.keys():
            if key in DU_SN:
                self.displayedDUtype = key
                self.info_label.configure(text=' ')
                self.canvas.create_rectangle(40, 40, 360, 540, fill=data.fillColor_SU)
                for mod in data.allDUs[self.displayedDUtype]:
                    self.canvas_place_rounded_rectangle(mod['x'], mod['y'], mod['w'], mod['h'])
                self.canvas.create_text(140, 475, text=self.displayedDUtype, anchor='nw', font=('Arial',50), fill=data.fillColor_SU_Text)
                self.canvas.create_text(145, 20, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text)
                self.canvas.create_text(145, 545, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text)
                if 'FI10' in DU_SN:
                    self.canvas.create_text(360, 290, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                    self.canvas.create_text(20, 290, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                # get the children of that DU, interested in Modules only here
                try:
                    self.partstree, self.last_responseText = util.get_children(parentDU_partID)
                    detector, self.last_responseText = util.get_parents(parentDU_partID)
                except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != '200':
                    self.api_status = 0
                    self.progressbar.configure(progress_color="#ff0000")
                    info_text = wrapped_text.fill(f'Error: DU relations could not be loaded from ProdDB API.\n{self.last_responseText}')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    self.this_DU_relations_MODULE = []
                    break
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color="#007711")
                    self.this_DU_fully_loaded = False
                    for r in self.partstree:
                        if str(r['part_parent']['part_id']) == str(parentDU_partID):
                            if str(r['part']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Module']):
                                self.this_DU_relations_MODULE.append(r)
                                # make the corresponding slot green
                                for mod in data.allDUs[self.displayedDUtype]:
                                    if mod['slot'] == str(r['position']):
                                        self.canvas_place_rounded_rectangle(mod['x'], mod['y'], mod['w'], mod['h'], fill=data.fillColor_AlreadyLoadedSlot)
                    if len(self.this_DU_relations_MODULE) == len(data.allDUs[self.displayedDUtype]):
                        self.canvas.create_text(380, 475, text='Fully loaded DU', anchor='nw', fill=data.fillColor_SU_Text)
                    if detector != []:
                        # this DU was already placed somewhere in the detector!!
                        for r in detector:
                            self.duAlreadyPlacedText = self.canvas.create_text(380, 525, text=f'Already placed at:\n{r['position']}', anchor='nw', fill=data.fillColor_SU_Text)
                    break
        else:
            info_text = 'Warning: Detector Unit type could not be retrieved from DU SN.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)

    def fetch_p_c(self, p, c):
        try:
            self.possible_parents, self.last_responseText = util.get_relevant_parts(p)
            self.possible_children, self.last_responseText = util.get_relevant_parts(c)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")
            self.possible_parents_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.combobox_parent.configure(values=self.possible_parents_SNs)
            self.combobox_child.configure(values=self.possible_children_SNs)

    def fetch_slots(self):
        try:
            self.slots, self.last_responseText = util.get_relevant_parts('Slot', getFullAttributes = True, useLocal = True)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.slots = None
            self.last_responseText = str(e)
        except ValueError as e:
            self.slots = None
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Slots could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")

    def update_progressbar(self, thread):
        if thread.is_alive():
            # update progressbar
            self.progressbar.step()
            self.after(250, self.update_progressbar, thread)
            self.progressbar.configure(progress_color="#BBAA00")
        else:
            self.progressbar.set(1)
            if self.api_status == 0:
                self.progressbar.configure(progress_color="#ff0000")
            else:
                self.progressbar.configure(progress_color="#007711")

if __name__ == "__main__":
    app = App()
    app.mainloop()
