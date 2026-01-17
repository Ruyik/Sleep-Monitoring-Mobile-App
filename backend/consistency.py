class ConsistencyCalculator:
    def calculate(self, extension_list):
        if not extension_list:
            return 100  # perfect

        avg_ext = sum(extension_list) / len(extension_list)

        # max extension = 180 mins → poor = 0 %
        score = max(0, 100 - (avg_ext / 180) * 100)
        return round(score, 2)
