# Save as: vcd_processor.py
# %%
import numpy as np
import pandas as pd
from vcd.reader import TokenKind, tokenize
import io

# %%

class VCDProcessor:
    """
    Loads, parses, and processes a SINGLE VCD (Value Change Dump) file
    to generate power traces based on signal activity.
    """

    VALID_POWER_MODELS = {'Identity', 'HammingWeight'}

    def __init__(self, vcd_path: str):
        self.vcd_path = vcd_path
        self.vars_df = pd.DataFrame()
        self.value_changes_arr = np.array([])
        self.sig_id_lookup = np.array([])
        
        try:
            scopes_raw, vars_raw, value_changes_raw = self._parse_vcd()
            if not vars_raw:
                print(f"Warning: No variables found in {vcd_path}")
                return # Can't process data if no vars
            
            self._process_data(scopes_raw, vars_raw, value_changes_raw)
        
        except FileNotFoundError:
            print(f"Error: VCD file not found at {self.vcd_path}")
            raise
        except Exception as e:
            print(f"Error initializing VCDProcessor for {self.vcd_path}: {e}")
            # Allow partial initialization if parsing fails mid-way
            pass


    def _parse_vcd(self) -> (list, list, list):
        """Parses the VCD file and extracts raw data."""
        with open(self.vcd_path, 'rb') as f:
            vcd_bytes = f.read()

        vcd_io = io.BytesIO(vcd_bytes)
        tokens = tokenize(vcd_io)

        scopes = []
        vars_raw = []
        value_changes_raw = []
        curr_scope = None
        curr_timestamp = 0

        for token in tokens:
            match token.kind:
                case TokenKind.SCOPE:
                    curr_scope = [token.data.ident, token.data.type_.name]
                    scopes.append(curr_scope)
                case TokenKind.UPSCOPE:
                    if scopes: scopes.pop()
                    curr_scope = scopes[-1] if scopes else None
                case TokenKind.VAR:
                    if curr_scope:
                        vars_raw.append([
                            curr_scope[0],
                            " -> ".join([s[0] for s in scopes]),
                            token.data.type_.value,
                            token.data.size,
                            token.data.id_code,
                            token.data.reference
                        ])
                case TokenKind.CHANGE_TIME:
                    curr_timestamp = token.data
                case TokenKind.CHANGE_VECTOR:
                    value_changes_raw.append([
                        curr_timestamp,
                        token.data.id_code,
                        token.data.value
                    ])
                case TokenKind.CHANGE_SCALAR:
                    value_changes_raw.append([
                        curr_timestamp,
                        token.data.id_code,
                        token.data.value
                    ])
        
        return scopes, vars_raw, value_changes_raw

    def _process_data(self, scopes_raw, vars_raw, value_changes_raw):
        """Converts raw parsed lists into structured formats."""
        self.vars_df = pd.DataFrame(
            vars_raw,
            columns=['Scope', 'Scope Chain', 'Type', 'Size', 'ID', 'Name']
        )
        self._build_compressed_scopes()
        self._factorize_signal_ids()
        self.value_changes_arr = np.array(value_changes_raw, dtype=object)

    def _get_scopes_for_id(self, curr_ID: str) -> list:
        """Helper to find unique, shortest scope chains for a signal ID."""
        df_for_curr_id = self.vars_df[self.vars_df.ID == curr_ID]
        scope_chain_curr_id = df_for_curr_id["Scope Chain"].to_list()
        sorted_scopes = sorted(scope_chain_curr_id, key=lambda s: s.count('->'))
        results = []
        for scope in sorted_scopes:
            if not any(scope != other and scope in other for other in sorted_scopes):
                results.append(scope)
        return results

    def _build_compressed_scopes(self):
        self.vars_df['Scopes Compressed'] = self.vars_df['ID'].apply(self._get_scopes_for_id)

    def _factorize_signal_ids(self):
        sig_idx, sig_id = pd.factorize(self.vars_df.ID)
        self.vars_df["signal_idx"] = sig_idx
        self.sig_id_lookup = sig_id

    def idx2id(self, idx: list) -> np.ndarray:
        """Converts a list of numeric signal indices back to their string IDs."""
        return np.array(self.sig_id_lookup[idx])

    def get_trace(self, power_model: str, filter_ids: list = None, fixed_timesteps: int = None) -> (np.ndarray, list):
        """
        Generates a power trace from the processed VCD data.

        Args:
            power_model (str): 'Identity' or 'HammingWeight'.
            filter_ids (list, optional): List of string signal IDs to include.
            fixed_timesteps (int, optional): If provided, the trace will be
                exactly this many timesteps long (padding or truncating).
                THIS IS REQUIRED FOR BATCH PROCESSING.

        Returns:
            A tuple of (power_trace, signal_names).
        """
        if power_model not in self.VALID_POWER_MODELS:
            raise ValueError(f"Invalid power model: {power_model}")
        
        if self.value_changes_arr.size == 0:
            return np.zeros((fixed_timesteps or 0, 0)), []

        # Filter array based on the provided list of string IDs
        if filter_ids is not None:
            filter_mask = np.isin(self.value_changes_arr[:, 1], filter_ids)
            arr = np.array(self.value_changes_arr[filter_mask], dtype=object)
        else:
            arr = np.array(self.value_changes_arr, dtype=object)

        if arr.size == 0:
            # Return an empty trace of the correct shape if filter yields no signals
            num_signals = len(filter_ids) if filter_ids is not None else 0
            return np.zeros((fixed_timesteps or 0, num_signals)), []

        t = arr[:, 0].astype(int)
        sid = arr[:, 1]
        val_str = arr[:, 2]

        # Handle non-numeric VCD values
        val_str[val_str == 'x'] = '0'
        val_str[val_str == 'z'] = '0'
        val = val_str.astype(object)

        # --- Handle fixed_timesteps ---
        if fixed_timesteps:
            num_timesteps = fixed_timesteps
            if t.max() >= num_timesteps:
                # Filter out events that happen at or after the cutoff time
                time_filter_mask = t < num_timesteps
                t = t[time_filter_mask]
                sid = sid[time_filter_mask]
                val = val[time_filter_mask]
                if t.size == 0: # All events were truncated
                    t = np.array([0])
                    sid = np.array([sid[0]]) # Use one sid to get num_signals
                    val = np.array([0]) # Use 0 as a default value
        else:
            num_timesteps = t.max() + 1
        
        # Map string IDs → column indices
        sig_idx, sig_labels = pd.factorize(sid)
        signal_names = sig_labels.tolist()
        num_signals = len(sig_labels)

        A = np.full((num_timesteps, num_signals), np.nan, dtype=float)
        
        # Write changes at their timestamps (t should be safe now)
        A[t, sig_idx] = val

        # Forward-fill (vectorized)
        mask = ~np.isnan(A)
        last = np.where(mask, np.arange(num_timesteps)[:, None], -1)
        np.maximum.accumulate(last, axis=0, out=last)
        last = last.clip(min=0)
        A_filled = A[last, np.arange(num_signals)]
        
        # Handle signals that were never initialized (still NaN) by setting to 0
        A_filled = np.nan_to_num(A_filled, copy=False, nan=0.0)

        # Apply power model
        if power_model == 'Identity':
            power_trace = A_filled.astype(int)
        elif power_model == 'HammingWeight':
            power_trace = np.bitwise_count(A_filled.astype(int))
        
        return power_trace, signal_names

# %%
