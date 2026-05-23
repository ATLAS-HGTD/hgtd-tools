# GUI component naming and patterns
Typical GUI elements and the associated actions, use these as examples to model additional components.

## Buttons associated with textbox

### Definition of elements, initial states
```python
        # frame containing textbox and button
        self.frame_sn_filter = customtkinter.CTkFrame(self.frame_child)
        # place the frame wrt parent frame
        self.frame_sn_filter.grid(
            row=3, column=0, padx=20, pady=(10, 10), sticky="nsew"
        )
        # variable to store input
        self.sn_filter_variable = customtkinter.StringVar(value="")
        # textbox
        self.sn_filter_entry = customtkinter.CTkEntry(
            self.frame_sn_filter, textvariable=self.sn_filter_variable
        )
        # place the textbox wrt parent frame
        self.sn_filter_entry.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        # definition of image to include with button
        self.filter_image = customtkinter.CTkImage(
            Image.open("searchIcon.png"), size=(20, 20)
        )
        # button
        self.btnFilterSN = customtkinter.CTkButton(
            self.frame_sn_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=self.button_filter_child_SN_event,
            width=60,
        )
        # place the button wrt parent frame
        self.btnFilterSN.grid(row=0, column=1, padx=5, pady=5, columnspan=2)
```

### Function handling button click
```python
    def button_filter_child_SN_event(self):
        self.combobox_child.set("- Select -")

        if self.operation_mode == "Module Loading":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector Unit", "Module")
            )
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "Detector Unit")
            )
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "PEB")
            )
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

```
