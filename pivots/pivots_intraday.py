from pivots.pivots import PivotsBase, PivotType, LocalPivot, GlobalPivot, get_dttime_form_intdt
from pivots.lib import abs_pct_chg


class IntradayPivots(PivotsBase):
    
    """
    
    Attributes inherited from PivotsBase:
    - current_tick: Current tick being processed
    - previous_tick: Previous tick processed
    - maxima_tick
    - minima_tick
    
    """

    def __init__(self, interval, num_bars=2):
        
        super().__init__(interval)
        self.past_bars = []
        self.probable_minima = dict()
        self.probable_maxima = dict()
        self.num_bars = num_bars
        self.past_tick = None


    def on_tick_custom(self, tick):


        self.debug = True if self.is_debug_duration(tick) else False

           
        pivot_marked = self._mark_subsequent_intraday_pivots(tick)
           
    
        if not pivot_marked:
            if self.interval == 5:
                debug = True
                
            self.past_bars.append(tick) 
            self.mark_global_pivot()
        




    def _is_new_day(self):
        """Check if it's a new trading day or if the pivot is uninitialized."""
        return not self.previous_tick or self.previous_tick.dt != self.current_tick.dt





    def _mark_subsequent_intraday_pivots(self, tick):
        """Process the current tick to determine if it is a pivot point."""
        
        if self.latest_local_pivot_type == PivotType.high:
            return self.mark_local_minima(tick)
        else:
            return self.mark_local_maxima(tick)
        
    

    def _mark_first_intraday_pivot(self, tick):
        """Mark the first intraday pivot point."""
        return self.mark_local_minima(tick) or self.mark_local_maxima(tick)
        
    
    def is_lower_close(self, close, past_tick):
        return close.close < past_tick.close and close.low < past_tick.low


    def is_higher_close(self, close, past_tick):
        return close.close > past_tick.close and close.high > past_tick.high


    def mark_local_minima(self, tick):
        close = tick.close
        prev_tick = None

        past_tick_i = len(self.past_bars) - 1

        while past_tick_i >= 0:

            past_tick = self.past_bars[past_tick_i]
            prev_tick = self.past_bars[past_tick_i - 1] if past_tick_i > 0 else None

            if self.is_higher_close(tick, past_tick):

                if self.is_traditional_pivot_complete(past_tick, tick, PivotType.low):
                    self.mark_pivot(tick, PivotType.low)
                    return True

                # elif self.is_intraday_pivot_complete(prev_tick, past_tick, tick, PivotType.low):
                #     self.mark_pivot(tick, PivotType.low)
                #     return True

                self.probable_minima[past_tick.tm] = self.probable_minima.get(past_tick.tm, []) + [tick]
            
            past_tick_i -= 1




    def mark_local_maxima(self, tick):

        close = tick.close
        prev_tick = None
        
        if tick.tm > 1514:
            debug=True

        past_tick_i = len(self.past_bars) -1
        while past_tick_i >= 0:

            past_tick = self.past_bars[past_tick_i]
            prev_tick = self.past_bars[past_tick_i - 1] if past_tick_i > 0 else self.past_tick

            if self.is_lower_close(tick, past_tick):

                if self.is_traditional_pivot_complete(past_tick, tick, PivotType.high):
                    self.mark_pivot(tick, PivotType.high)
                    return True

                # elif self.is_intraday_pivot_complete(prev_tick, past_tick, tick, PivotType.high):
                #     self.mark_pivot(tick, PivotType.high)
                #     return True

                self.probable_maxima[past_tick.tm] = self.probable_maxima.get(past_tick.tm, []) + [tick]
            
            past_tick_i -= 1




    def is_traditional_pivot_complete(self, pivot_tick, tick, pivot_type):
        if pivot_type == PivotType.high:
            num_bars = len(self.probable_maxima.get(pivot_tick.tm, []))
        else:
            num_bars = len(self.probable_minima.get(pivot_tick.tm, []))

        if not num_bars + 1 >= self.num_bars:
            return False
        
        return True

        # # check if tick is atlest half of pivot tick
        # if pivot_type == PivotType.high:
        #     return tick.close < (pivot_tick.open + pivot_tick.close) / 2
        # else:
        #     return tick.close > (pivot_tick.open + pivot_tick.close) / 2
        


    def is_intraday_pivot_complete(self, prev_tick, pivot_tick, tick, pivot_type):

        if prev_tick is None or self.get_tick_body_pct(prev_tick) < 0.03:
            return False

        # https://mo neyball.fibery.io/Software_Development/bug/pivot-marking-to-be-made-conservative-4
        
        if pivot_type == PivotType.high:
            if (tick.close < prev_tick.close 
                and tick.close <= prev_tick.oc_l 
                # and pivot_tick.close > prev_tick.close
                ):
                return True
        else:
            if (tick.close > prev_tick.close
                and tick.close > prev_tick.oc_h
                # and pivot_tick.close < prev_tick.close
                ):
                return True

        return False
        



    def remark_local_pivot(self, pivot_type):
        if pivot_type == PivotType.low:
            if not self.local_minima:
                return

            pivot = self.local_minima[-1]
            alternate_pivot = self.local_maxima[-1]
            if get_dttime_form_intdt(self.minima_tick.dt, self.minima_tick.tm) >= alternate_pivot.ts:
                return
            
            if self.minima_tick.dt != pivot.tick.dt:
                return
            
            if pivot.tick.close > self.minima_tick.close:
                pivot.tick = self.minima_tick
                
            
        else:
            if not self.local_maxima:
                return

            pivot = self.local_maxima[-1]
            alternate_pivot = self.local_minima[-1]

            if get_dttime_form_intdt(self.maxima_tick.dt, self.maxima_tick.tm) >= alternate_pivot.ts:
                return

            if self.maxima_tick.dt != pivot.tick.dt:
                return 
            
            if pivot.tick.close < self.maxima_tick.close:
                pivot.tick = self.maxima_tick


    def mark_pivot(self, formation_tick, pivot_type):
        
        self.latest_local_pivot_type = pivot_type
        
        if formation_tick.tm > 1519:
            debug = True
            
        if pivot_type == PivotType.high:
            pivot = LocalPivot(self.maxima_tick, pivot_type, formation_tick)

            self.local_maxima.append(pivot)
            self.remark_local_pivot(PivotType.low)

            # resetting minima tick here, should be reset to the min of all the bars starting from maxima_tick
            
            self.minima_tick = self.search_min_max_tick(self.maxima_tick, find='min')

            self.probable_maxima = dict()

        else:
            pivot = LocalPivot(self.minima_tick, pivot_type, formation_tick)

            self.local_minima.append(pivot)
            self.remark_local_pivot(PivotType.high)
            
            self.maxima_tick = self.search_min_max_tick(self.minima_tick, find='max')
            self.probable_minima = dict()

        self.locals.append(pivot)
        dt = pivot.tick.dt
        self.local_map[dt] = self.local_map.get(dt, []) + [pivot]
        
        self.past_tick = self.past_bars[-1]
        self.past_bars = [self.current_tick]
      
      
    def search_min_max_tick(self, pivot_tick, find='min'):
        min_max_tick = None
        
        i = -1
        tick = self.current_tick
        
        if find == 'min':
            while True:

                if min_max_tick is None or tick.low < min_max_tick.low:
                    min_max_tick = tick
                    
                if (tick.dt == pivot_tick.dt and tick.tm == pivot_tick.tm) or i == -len(self.ticks):
                    break
                
                tick = self.ticks[i]
                i -= 1
                
                
        else:
            while True:
            
                if min_max_tick is None or  tick.high > min_max_tick.high:
                    min_max_tick = tick

                if (tick.dt == pivot_tick.dt and tick.tm == pivot_tick.tm) or i == -len(self.ticks):
                    break
                tick = self.ticks[i]
                i -= 1
                
                
        return min_max_tick
    
        
    def mark_global_pivot(self):
        if self.latest_global_pivot_type is None:
            self.mark_first_global_pivot()
        
        else:
            self.mark_subsequent_global_pivots()
        
            
    
    def mark_subsequent_global_pivots(self):
        current_maxima = self.local_maxima[-1]
        current_minima = self.local_minima[-1]
        
        if self.latest_global_pivot_type == PivotType.high:
            if self.current_tick.close > current_maxima.tick.oc_h:
                self.add_global_pivot(current_minima.tick, PivotType.low)
                return
        else:
            if self.current_tick.close < current_minima.tick.oc_l:
                self.add_global_pivot(current_maxima.tick, PivotType.high)
                return
    
    def mark_first_global_pivot(self):
        local_pivots = self.locals
        if len(local_pivots) < 4:
            return
        
        """
        check for uptrend or downtrend
        """
        
        if local_pivots[-4].pivot_type == PivotType.low:
            # mark global high pivot
            higher_high_higher_low = local_pivots[-2].tick.oc_l > local_pivots[-4].tick.oc_l and local_pivots[-1].tick.oc_h > local_pivots[-3].tick.oc_h
            if higher_high_higher_low and self.current_tick.close < local_pivots[-2].tick.oc_l:
                self.add_global_pivot(local_pivots[-1].tick, PivotType.high)
                return
                
        
        elif local_pivots[-4].pivot_type == PivotType.high:
            lower_low_lower_high = local_pivots[-2].tick.oc_h < local_pivots[-4].tick.oc_h and local_pivots[-1].tick.oc_l < local_pivots[-3].tick.oc_l
            if lower_low_lower_high and self.current_tick.close > local_pivots[-2].tick.oc_h:
                self.add_global_pivot(local_pivots[-1].tick, PivotType.low)
                return
        
    
    def add_global_pivot(self, tick, pivot_type):
        
        self.latest_global_pivot_type = pivot_type

        if pivot_type == PivotType.high:
            pivot = GlobalPivot(tick, pivot_type, self.current_tick)
            self.global_maxima.append(pivot)
        else:
            pivot = GlobalPivot(tick, pivot_type, self.current_tick)
            self.global_minima.append(pivot)

        self.globals.append(pivot)
        dt = tick.dt
        self.global_map[dt] = self.global_map.get(dt, []) + [pivot]

        # Reset local pivots tracking
        self.past_bars = [self.current_tick]
        
        
    
    def is_debug_duration(self, tick):
        
        """Check if the current tick is part of a debug day."""
        if self.interval == 15:
            if tick.dt == 20180101:
                return True
            
        return False
    
    
    

    @staticmethod
    def get_tick_body_pct(tick):
        return abs_pct_chg(tick.close, tick.open)
    
    
class PivotManager:
    def __init__(self, freqs):
        self.pivots = {freq: IntradayPivots(freq) for freq in freqs if freq in [5, 15, 30]}

    def process_pivots(self, streamer):
        for freq in self.pivots:
            tick = getattr(streamer, f'tick_{freq}')
            if not tick:
                continue
            
            self.pivots[freq].on_tick(tick)
            
            
from datetime import datetime 
import pandas as pd

class Tick:
    def __init__(self, index, dttime, dt, tm, open_, high, low, close, volume):
        self.index = index
        self.dttime = dttime
        self.dt = dt
        self.tm = tm
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

        if self.open > self.close:
            self.oc_h = self.open
            self.oc_l = self.close
        else:
            self.oc_h = self.close
            self.oc_l = self.open

    def __repr__(self):
        return (f"Tick(index={self.index}, dt={self.dt}, tm={self.tm}, open={self.open}, "
                f"high={self.high}, low={self.low}, close={self.close}, "
                f"volume={self.volume}, oc_h={self.oc_h}, oc_l={self.oc_l})")
        
        
def convert_date_to_int(date_str):
    dt_obj = datetime.strptime(date_str, '%d.%m.%y %H:%M:%S')
    return int(dt_obj.strftime('%Y%m%d'))

# Load the Excel file
file_path = '~/Downloads/27Jan2022_NF_24Feb22_marked.xlsx'
excel_data = pd.read_excel(file_path)

# Populate the list of Tick objects with dt as an integer date format and tm as HHMM
ticks_with_dt_int = []

for idx, row in excel_data.iterrows():
    dttime = datetime.strptime(row['Date'], '%d.%m.%y %H:%M:%S')
    dt_int = convert_date_to_int(row['Date'])
    tm_int = int(dttime.strftime('%H%M'))  # Convert time to HHMM format (919 for 09:19)
    
    tick = Tick(
        idx, 
        dttime,
        dt_int, 
        tm_int, 
        row['Open'], 
        row['High'], 
        row['Low'], 
        row['Close'], 
        row['vol']
    )
    
    ticks_with_dt_int.append(tick)

stock_data = []
pivots = IntradayPivots(interval=5)
for tick in ticks_with_dt_int:
    pivots.on_tick(tick)