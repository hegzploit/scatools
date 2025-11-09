import numpy as np
import pandas as pd
from tqdm import tqdm
from .vcd_processor import VCDProcessor  # Import the package-local class

# %%

class VCDBatchProcessor:
    """
    Manages and processes a BATCH of VCD files to produce a stacked
    array of power traces.
    
    Assumes all VCD files share the same signal structure/definitions.
    """

    def __init__(self, vcd_file_paths: list):
        """
        Initializes the batch processor with a list of VCD file paths.

        Args:
            vcd_file_paths (list): A list of strings, where each string
                                   is a path to a .vcd file.
        """
        if not vcd_file_paths:
            raise ValueError("No VCD file paths provided.")
            
        self.vcd_paths = vcd_file_paths
        self.num_traces = len(vcd_file_paths)
        
        # Load the first VCD as a reference for metadata
        print(f"Using '{self.vcd_paths[0]}' as reference for signal definitions.")
        try:
            self.reference_processor = VCDProcessor(self.vcd_paths[0])
            self.vars_df = self.reference_processor.vars_df
            self.sig_id_lookup = self.reference_processor.sig_id_lookup
            print(f"Reference loaded. Found {len(self.vars_df)} signals.")
        except Exception as e:
            print(f"Error loading reference VCD: {e}")
            print("Cannot proceed with batch processing without a valid reference.")
            raise

    def idx2id(self, idx: list) -> np.ndarray:
        """
        Converts a list of numeric signal indices back to their string IDs
        (based on the reference VCD file).
        """
        return self.reference_processor.idx2id(idx)

    def process_traces(self, 
                       power_model: str, 
                       filter_ids: list, 
                       fixed_timesteps: int, 
                       sum_signals: bool = True, 
                       show_progress: bool = True) -> np.ndarray:
        """
        Processes all VCD files and stacks their traces into a single array.

        Args:
            power_model (str): 'Identity' or 'HammingWeight'.
            filter_ids (list): List of string signal IDs to trace.
            fixed_timesteps (int): The exact number of timesteps for each trace.
                                   This is REQUIRED for stacking.
            sum_signals (bool, optional): If True, sums the granular trace
                (axis 1) to produce a 1D trace per VCD. Defaults to True.
            show_progress (bool, optional): If True, displays a tqdm progress bar.

        Returns:
            np.ndarray: A stacked array of traces.
            - If sum_signals=True: Shape is (num_traces, fixed_timesteps)
            - If sum_signals=False: Shape is (num_traces, fixed_timesteps, num_signals)
        """
        all_traces = []
        
        iterator = self.vcd_paths
        if show_progress:
            iterator = tqdm(self.vcd_paths, desc="Processing VCDs")

        for path in iterator:
            try:
                proc = VCDProcessor(path)
                
                # Use the modified get_trace with fixed_timesteps
                granular_trace, mappings = proc.get_trace(
                    power_model=power_model,
                    filter_ids=filter_ids,
                    fixed_timesteps=fixed_timesteps
                )
                
                if granular_trace.size == 0:
                     print(f"Warning: No data generated for {path}. Skipping.")
                     continue
                
                if sum_signals:
                    # Sum across signals (axis 1)
                    trace = granular_trace.sum(axis=1)
                else:
                    # Keep the granular 2D trace
                    trace = granular_trace
                
                all_traces.append(trace)
                
            except Exception as e:
                print(f"Failed to process {path}: {e}. Skipping this file.")
                pass
        
        if not all_traces:
            print("Error: No traces were successfully processed.")
            return np.array([])
            
        try:
            # Stack all traces into a single NumPy array
            # axis=0 creates the (num_traces, ...) shape
            stacked_traces = np.stack(all_traces, axis=0)
            return stacked_traces
        except ValueError as e:
            print(f"Error stacking traces: {e}")
            print("This is likely due to inconsistent shapes. Ensure all VCDs "
                  "produce a consistent trace.")
            return np.array(all_traces, dtype=object) # Return list as a fallback

# %%
if __name__ == "__main__":
    # --- Example Usage ---
    
    # 1. Define your list of VCD files
    # (Update this with your actual file paths)
    vcd_files = [
        '../trace1.vcd',
        '../trace2.vcd',
        '../trace3.vcd'
        # ... add all 100 or 1000 of your VCD files here
    ]
    
    # A known, fixed length for your simulation (e.g., 20000 cycles)
    # You MUST specify this to make all traces the same size.
    SIMULATION_TIMESTEPS = 20000 

    try:
        # 2. Initialize the batch processor
        # This will load the first VCD to get signal info
        batch_processor = VCDBatchProcessor(vcd_files)
        
        # 3. Get the string IDs for the signals you want to trace
        #    (using the helper from the batch processor)
        #    Example: Get IDs for signal indices 1, 2, and 3
        signal_indices = [1, 2, 3]
        my_filter_ids = batch_processor.idx2id(signal_indices).tolist()
        print(f"\nTracing signals with IDs: {my_filter_ids}")
        
        # 4. Process all traces!
        print("Starting batch processing...")
        power_traces_array = batch_processor.process_traces(
            power_model='HammingWeight',
            filter_ids=my_filter_ids,
            fixed_timesteps=SIMULATION_TIMESTEPS,
            sum_signals=True  # Get a (num_traces, timesteps) array
        )
        
        print(f"\nProcessing Complete!")
        print(f"Shape of final traces array: {power_traces_array.shape}")
        # Expected output: (3, 20000) if you have 3 files
        
        
        # 5. Example: Get a 3D "granular" trace array
        print("\nProcessing granular traces (sum_signals=False)...")
        granular_traces_array = batch_processor.process_traces(
            power_model='HammingWeight',
            filter_ids=my_filter_ids,
            fixed_timesteps=SIMULATION_TIMESTEPS,
            sum_signals=False # Get a (num_traces, timesteps, num_signals) array
        )

        print(f"\nProcessing Complete!")
        print(f"Shape of final granular array: {granular_traces_array.shape}")
        # Expected output: (3, 20000, 3) if you have 3 files and 3 signals
        

    except FileNotFoundError:
        print(f"\n*** TEST FAILED: Please update the 'vcd_files' list "
              f"in the if __name__ == '__main__': block to point to your files. ***")
    except Exception as e:
        print(f"\n*** An unexpected error occurred: {e} ***")
