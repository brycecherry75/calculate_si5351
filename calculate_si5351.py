import argparse, sys, math

# Integer or Fractional mode can be used for the PLL and the channel
# MultiSynth divider in any combination except that certain channels cannot
# use Fractional mode (only Integer mode with even division ratios 6-254 is
# allowed) for the MultiSynth divider.
#
# Integer mode:
# PLL frequency = Reference freqeuency * PLL Integer
# Output frequency = PLL frequency / MultiSynth Integer / R divider
#
# Fractional mode:
# PLL frequency = Reference freqeuency * (PLL Integer + (PLL Fraction / PLL Modulus))
# Output frequency = PLL frequency / (MultiSynth Integer + (MultiSynth Fraction / MultiSynth Modulus)) / R divider
#
# Unless noted, these are datasheet values which are to be observed for the above formulae:
Reference_MinimumFrequency = 10000000 # Hz
Reference_MaximumFrequency = 100000000 # Hz
Output_MaximumFrequency = 160000000 # Hz
PLL_MinimumFrequency = 600000000 # Hz as per Adafruit_CircuitPython_SI5351 example
PLL_MaximumFrequency = 900000000 # Hz as per Adafruit_CircuitPython_SI5351 example
PLL_FractionalBits = 20 # as per Adafruit_CircuitPython_SI5351
PLL_IntegerBits = 7 # as per Adafruit_CircuitPython_SI5351
PLL_MinimumInteger = 15 # as per Adafruit_CircuitPython_SI5351
PLL_MaximumInteger = 90 # as per Adafruit_CircuitPython_SI5351
MultiSynth_IntegerBits_FractionalChannels = 18
MultiSynth_FractionalBits_FractionalChannels = 20
MultiSynth_IntegerBits_IntegerChannels = 8
MultiSynth_IntegerOnlyChannels = [False, False, False, False, False, False, True, True]
MultiSynth_IntegerOnlyMinimumValue = 6
MultiSynth_MinimumInteger = 4 # as per Adafruit_CircuitPython_SI5351
MultiSynth_MaximumInteger = 2048 # as per Adafruit_CircuitPython_SI5351
MultiSynth_R_Dividers = 7 # powers of 2
MultiSynth_MinimumOutputFrequency = 1000000 # Hz before R divider on each channel
ChannelCount = 8 # for "B/C" suffix devices; "A" suffix devices have three channels (this constant does not need to be changed)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
  parser.add_argument("--outfreq", type=float, required='yes', help="Desired output frequency in Hz")
  parser.add_argument("--pllfreq", type=float, default=900000000, help="Desired PLL frequency in Hz (default: 900 MHz)")
  parser.add_argument("--ref", type=float, default=10000000, help="Reference frequency in Hz (default: 10 MHz)")
  parser.add_argument("--channel", type=int, default=0, help="Channel (default: 0)")
  args = parser.parse_args()

  if (MultiSynth_IntegerOnlyMinimumValue % 2) != 0:
    print("ERROR: MultiSynth_IntegerOnlyMinimumValue is not even")
    sys.exit(0)
  if len(MultiSynth_IntegerOnlyChannels) != ChannelCount:
    print("ERROR: ChannelCount and MultiSynth_IntegerOnlyChannels size mismatch")
    sys.exit(0)
  if args.channel < 0 or args.channel >= ChannelCount:
    print("ERROR: Channel is not within 0-" + str((ChannelCount - 1)))
    sys.exit(0)
  if args.ref < Reference_MinimumFrequency or args.ref > Reference_MaximumFrequency:
    print("ERROR: Reference frequency is not within", str((Reference_MinimumFrequency / 1000000)) + "-" + str((Reference_MaximumFrequency / 1000000)), "MHz")
    sys.exit(0)
  if args.pllfreq < PLL_MinimumFrequency or args.pllfreq > PLL_MaximumFrequency:
    print("ERROR: PLL frequency is not within", str((PLL_MinimumFrequency / 1000000)) + "-" + str((PLL_MaximumFrequency / 1000000)), "MHz")
    sys.exit(0)
  if args.pllfreq < args.ref:
    print("ERROR: PLL frequency is lower than reference frequency")
    sys.exit(0)
  MaximumPLLratio = (PLL_MaximumInteger + (((1 << PLL_FractionalBits) - 2) / ((1 << PLL_FractionalBits) - 1)))
  if int(args.pllfreq / args.ref) > MaximumPLLratio:
    print("ERROR: PLL/Reference frequency ratio is greater than", MaximumPLLratio)
    sys.exit(0)
  if int(args.pllfreq / args.ref) < PLL_MinimumInteger:
    print("ERROR: PLL/Reference frequency ratio is less than", PLL_MinimumInteger)
    sys.exit(0)
  MinimumFrequency = math.ceil(MultiSynth_MinimumOutputFrequency / (1 << MultiSynth_R_Dividers))
  MaximumFrequency = args.pllfreq / MultiSynth_MinimumInteger
  if MultiSynth_IntegerOnlyChannels[args.channel] == True:
    MinimumFrequency = math.ceil(args.pllfreq / ((1 << MultiSynth_IntegerBits_IntegerChannels) - 2) / (1 << MultiSynth_R_Dividers)) # an even division ratio is required as per datasheet
    MaximumFrequency = args.pllfreq / MultiSynth_IntegerOnlyMinimumValue
  if MaximumFrequency > Output_MaximumFrequency:
    MaximumFrequency = Output_MaximumFrequency
  if args.outfreq > MaximumFrequency:
    print("ERROR: Output frequency exceeds", str(MaximumFrequency / 1000000), "MHz for this channel and PLL frequency")
    sys.exit(0)
  if args.outfreq < MinimumFrequency:
    print("ERROR: Output frequency is less than", MinimumFrequency, "Hz for this channel and PLL frequency")
    sys.exit(0)

  PLL_int = args.pllfreq / args.ref
  PLL_int_remainder = PLL_int - int(PLL_int)
  PLL_int = int(PLL_int)
  PLL_error = args.pllfreq
  PLL_frac = 0
  PLL_mod = 0
  if PLL_int_remainder > 0:
    for ModToTry in range ((1 << PLL_FractionalBits)):
      if ModToTry >= 2:
        frac_to_check = int(ModToTry * PLL_int_remainder)
        if frac_to_check > 0:
          if int(frac_to_check + 0.5) < ModToTry:
            frac_to_check = int((ModToTry * PLL_int_remainder) + 0.5) # will need to recalculate - rounding with adding 0.5 and converting to integer results in loss of precision
          Current_PLL_error = PLL_int_remainder - (frac_to_check / ModToTry)
          if Current_PLL_error < 0:
            Current_PLL_error *= -1
          if Current_PLL_error < PLL_error:
            PLL_error = Current_PLL_error
            PLL_frac = frac_to_check
            PLL_mod = ModToTry
            if PLL_error == 0:
              break

  if PLL_frac > 0 and PLL_mod > 0:
    Actual_PLL_freq = (args.ref * (PLL_int + (PLL_frac / PLL_mod)))
  else:
    Actual_PLL_freq = args.ref * PLL_int
  PLL_error = args.pllfreq - Actual_PLL_freq
  print("PLL Integer:", PLL_int)
  if PLL_frac > 0 and PLL_mod > 0:
    print("PLL operating uder Fractional mode")
    print("PLL Fraction:", PLL_frac)
    print("PLL Modulus:", PLL_mod)
  else:
    print("PLL operating under Integer mode")
  if PLL_error != 0:
    print("PLL frequency error is", PLL_error, "Hz")
  else:
    print("PLL frequency has no error")

  MultiSynth_int = 1
  R_div = 1
  if args.outfreq < MultiSynth_MinimumOutputFrequency:
    for DividerToTry in range (MultiSynth_R_Dividers):
      if (args.outfreq * R_div) >= MultiSynth_MinimumOutputFrequency:
        break
      R_div *= 2

  if MultiSynth_IntegerOnlyChannels[args.channel] == False:
    MultiSynth_int = Actual_PLL_freq / R_div / args.outfreq
    MultiSynth_int_remainder = MultiSynth_int - int(MultiSynth_int)
    MultiSynth_int = int(MultiSynth_int)
    MultiSynth_error = args.pllfreq
    MultiSynth_frac = 0
    MultiSynth_mod = 0
    if MultiSynth_int_remainder > 0:
      for ModToTry in range ((1 << MultiSynth_FractionalBits_FractionalChannels)):
        if ModToTry >= 2:
          frac_to_check = int(ModToTry * MultiSynth_int_remainder)
          if int(frac_to_check + 0.5) < ModToTry:
            frac_to_check = int((ModToTry * MultiSynth_int_remainder) + 0.5) # will need to recalculate - rounding with adding 0.5 and converting to integer results in loss of precision
          if frac_to_check > 0:
            Current_MultiSynth_error = MultiSynth_int_remainder - (frac_to_check / ModToTry)
            if Current_MultiSynth_error < 0:
              Current_MultiSynth_error *= -1
            if Current_MultiSynth_error < MultiSynth_error:
              MultiSynth_error = Current_MultiSynth_error
              MultiSynth_frac = frac_to_check
              MultiSynth_mod = ModToTry
              if MultiSynth_error == 0:
                break
  else:
    R_div = 1
    MultiSynth_int = Actual_PLL_freq / args.outfreq
    for DividerToTry in range (MultiSynth_R_Dividers):
      if MultiSynth_int < ((1 << MultiSynth_IntegerBits_IntegerChannels) - 1 - 0.5): # an even division ratio is required as per datasheet
        break
      R_div *= 2
      MultiSynth_int /= 2
    if (int(MultiSynth_int + 0.5) % 2) == 0:
      MultiSynth_int = int(MultiSynth_int + 0.5)
    else: # rounding to an even division ratio is required as per datasheet
      RoundedMultipleLow = int(MultiSynth_int + 0.5) - 1
      RoundedMultipleHigh = int(MultiSynth_int + 0.5) + 1
      if (MultiSynth_int - RoundedMultipleLow) < (RoundedMultipleHigh - MultiSynth_int):
        MultiSynth_int = RoundedMultipleLow
      else:
        MultiSynth_int = RoundedMultipleHigh

  if MultiSynth_IntegerOnlyChannels[args.channel] == False and MultiSynth_frac > 0 and MultiSynth_mod > 0:
    Actual_freq = ((Actual_PLL_freq / (MultiSynth_int + (MultiSynth_frac / MultiSynth_mod))) / R_div)
  else:
    Actual_freq = Actual_PLL_freq / MultiSynth_int / R_div

  freq_error = Actual_freq - args.outfreq
  print("MultiSynth Integer:", MultiSynth_int)
  if MultiSynth_IntegerOnlyChannels[args.channel] == False and MultiSynth_frac > 0 and MultiSynth_mod > 0:
    print("MultiSynth operating under Fractional mode")
    print("MultiSynth Fraction:", MultiSynth_frac)
    print("MultiSynth Modulus:", MultiSynth_mod)
  else:
    print("MultiSynth operating under Integer mode")
  print("MultiSynth R divider:", R_div)
  if freq_error != 0:
    print("Output frequency error is", freq_error, "Hz")
  else:
    print("Output frequency has no error")