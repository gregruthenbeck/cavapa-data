import csv
from datetime import datetime, time
from dateutil import parser as timeParser
import numpy as np
from scipy import stats
import decimal

# Util class for reading CSV data from cavapaGPU.exe
# Expected CSV format from cavapaGPU.exe:
# 25,00:00:01,35
class TimeScore:
	def __init__(self, id, t, score): 
		self.id = id # int. row ID
		self.time = t # expects datetime
		self.score = score # int
	def __str__(self):
		return f'ID: {self.id}, Time: {self.time.strftime("%H:%M:%S")}, Score: {self.score}'

class TimeLevels:
	def __init__(self, id, t, levels): 
		self.id = id # int. row ID
		self.time = t # expects datetime
		self.levels = levels # expects int[4]
		self.score = levelsToScore(levels) # int
	def __str__(self):
		return f'ID: {self.id}, Time: {self.time.strftime("%H:%M:%S")}, Levels: {self.levels}, Score: {self.score}'

# function: levelsToScore(level) -> int:
# Convert observed activity levels from counts of the 4 levels to SI-units
# Based on SOPLAY (derived from SOPARC)
# McKenzie, Thomas L. "System for observing play and leisure activity in youth (SOPLAY)." Retrieved August 1 (2002): 2006.
# 	Sedentary: 	.051kcal/kg/min, 
# 	Walking: 	.096kcal/kg/min, 
# 	Very active: .144kcal/kg/min.
# We observed 4 activity leves (not 3), so we add a "standing" value of around 0.072
#  so that we can compare CAVAPA by converting activity levels as:
# 	Sedentary count * 51 +
# 	Standing count * 72 +
# 	Walking count * 96 +
# 	High-activity count * 144
def levelsToScore(levels) -> int:
	#m = [51,72,96,144]
	m = [1,2,3,4] # multipliers
	total = 0
	for i in range(0,4):
		total = total + m[i] * levels[i]
	return total

# Read Activity Levels Data from CSV (as output from VOST)
# Expected line format:
#  1,00:00:10,1.2.3.4
def readTimeLevelsCSV(fname: str):
	data = []
	with open(fname, newline='') as csvfile:
		testreader = csv.reader(csvfile, delimiter=',', quotechar='|')
		count = 0
		for row in testreader:
			if row and len(row) > 2:
				row[1] = row[1].strip(', ')
				t = timeParser.parse(row[1])
				levels = row[2].split('.');
				levelsInt = []
				for l in levels:
					levelsInt.append(int(l))
				data.append(TimeLevels(count,t,levelsInt))
				count = count + 1
	return data

# data: TimeLevels[]
def getScoresFromTimeLevels(data):
	ret = []
	if type(data[0]) is TimeLevels or type(data[0]) is TimeScore: 
		for d in data:
			ret.append(d.score)
	else:
		for d in data:
			ret.append(int(d))
	return ret

# 
def readSimpleCSV(csvFilepath, fps = 1, intervalDurationSeconds = 1):
	downSample = fps * intervalDurationSeconds
	data = []
	with open(csvFilepath, newline='') as csvfile:
		testreader = csv.reader(csvfile, delimiter=',', quotechar='|')
		line = 0
		count = 0
		total = 0
		for row in testreader:
			line = line + 1
			try:
				if row and len(row) > 0:
					#row[1] = row[1].strip(', ')
					#dec = decimal.Parse(row[0]);
					d = float(row[0])
					count = count + 1
					if count % downSample == 0:
						data.append(d)
						total = d
					else:
						total = total + d
			except:
				print("Skipping CSV line ", line, ": ", row)
		return data

# Read Cavapa movement score from CSV (as output from cavapaGPU)
# Expected line format:
# 25,00:00:01,35
def readCavapaGpuCSV(fname: str):
	data = []
	with open(fname, newline='') as csvfile:
		testreader = csv.reader(csvfile, delimiter=',', quotechar='|')
		count = 0
		for row in testreader:
			if row and len(row) > 2:
				row[1] = row[1].strip(', ')
				t = timeParser.parse(row[1])
				score = int(row[2])
				data.append(TimeScore(count,t,score))
				count = count + 1
	return data

def downSample(data: list, dsCount: int) -> list:
	ret = []
	count = 0
	total = 0
	for d in data:
		count = count + 1
		total += d
		if count % dsCount == 0:
			ret.append(total / dsCount)
			total = 0
	return ret

def trimToSameLen(dataDict):
	minLen = 1E31
	for k,v in dataDict.items():
		minLen = min(minLen, len(v))
	ret = {}
	for k,v in dataDict.items():
		ret[k] = v[0:minLen]
	return ret

def trimArgsToSameLen(*args):
	minLen = 1E31;
	for a in args:
		minLen = min(minLen, len(a))
	ret = []
	for a in args:
		ret.append(a[0:minLen])
	return ret

# Expects *args to contain arrays of the same length
def writeArraysToCSV(fname: str, fileComment: str, *args):
	with open(fname, 'w') as file:
		file.write(f'# {fileComment}\n')
		for i in range(0,len(args[0])):
			for a in args:
				file.write(f'{a[i]},')
			file.write('\n')

# Expects dict to contain arrays of the same length
def writeDictToCSV(fname: str, fileComment: str, data):
	with open(fname, 'w') as file:
		file.write(f'# {fileComment}\n')
		keys = list(data.keys())
		# Write Column headings
		file.write(f'ID,') # row index
		for k in keys:
			file.write(f'{k},')
		file.write('\n')
		# Write data to file as columns
		for i in range(0,len(data[keys[0]])):
			file.write(f'{i},')
			for k in keys:
				if i < len(data[k]):
					file.write(f'{data[k][i]},')
				else:
					file.write(' ,')
			file.write('\n')

def readHeartRateRawCSV(fname: str):
	data = []
	with open(fname) as csvfile:
		reader = csv.reader(csvfile, delimiter=',', quotechar='"')
		headerRows = 3
		headerRowCount = 0
		count = 0
		for row in reader:
			if headerRowCount < headerRows:
				headerRowCount = headerRowCount + 1
			elif row:
				row[0] = row[0].strip(', ')
				chunk = row[0].split(',')
				if len(chunk) > 2:
					t = timeParser.parse(chunk[1])
					score = int(chunk[2])
				elif len(chunk) == 2:
					t = timeParser.parse(chunk[0])
					score = int(chunk[1])
				data.append(TimeScore(count,t,score))
				count = count + 1
	return data

def readHeartRateCSV(fname: str):
	data = []
	invalidCSVLValueCount = 0
	with open(fname) as csvfile:
		reader = csv.reader(csvfile, delimiter=',', quotechar='"')
		headerRows = 2
		headerRowCount = 0
		count = 0
		for row in reader:
			if headerRowCount < headerRows:
				headerRowCount = headerRowCount + 1
			elif row and len(row) > 7:
				total = 0
				for i in range(1,8):
					try:
						total = total + float(row[i])
					except:
						invalidCSVLValueCount += 1 # skip empty or invalid entries
				data.append(total / 7)
				count = count + 1
	if invalidCSVLValueCount:
		print(f'WARNING: Skipped {invalidCSVLValueCount} invalid cells in CSV fpath=\"{fname}\"')
	return data


def printCorrelation(dataDict):
	keys=list(dataDict.keys())
	series1 = dataDict[keys[0]]
	series2 = dataDict[keys[1]]
	corPears = stats.pearsonr(series1, series2)
	corrSpear = stats.spearmanr(series1,series2)
	print(f'{keys[0]}-{keys[1]}, \t' +
	      f'{corPears[0]:.2f}, ' +
	      f'{corrSpear.correlation:.2f}')
	# print(f'{label} {keys[0]}-{keys[1]}, ' +
	    #   f'({(int)(100 * corPears[0])}, { "{:.8f}".format(corPears[1]) }),' +
	    #   f'({(int)(100 * corrSpear.correlation)}, { "{:.8f}".format(corrSpear.pvalue)})')

from datetime import datetime, timedelta

def datetime_range(start, end, delta):
    current = start
    while current < end:
        yield current
        current += delta

def normalize(arr, t_min, t_max):
	ret = []
	diff = t_max - t_min
	diff_arr = max(arr) - min(arr)    
	for i in arr:
		temp = (((i - min(arr))*diff)/diff_arr) + t_min
		ret.append(temp)
	return ret
