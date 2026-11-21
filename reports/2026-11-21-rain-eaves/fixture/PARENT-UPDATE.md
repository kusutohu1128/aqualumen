Use build/Aqualumen-1.7.0-rain-rc2.zip for native tests. rc1 exceeds the Iris 1.8.8 limit of 16 custom images. Preserve existing receipts. Use rc2-specific output names.

Final candidate build/Aqualumen-1.7.0-rain-rc3.zip (SHA 2c81439353053f7adb12700eb3fb4ea9b9991169ee165a7963e182e9cb0ab4d9). New actual game measurement reveals Iris 1.8.8 misassigns the drynessHalflife directive to the rise field. Removed that directive to allow authentic ~6-second wetting and native ~20-second drying. Older rc2 has ~24-second wetting. Keep the baseline running; use rc3 going forward. Reading eaves measurements in real Minecraft confirmed glass/stone cover block rain.

Parent handed completed base-r1 to aql-rain-fixture-final-patio, which will collect rc3. Do not rerun the baseline.
