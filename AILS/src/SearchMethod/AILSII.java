package SearchMethod;

import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.text.DecimalFormat;
import java.util.HashMap;
import java.util.Random;

import Auxiliary.Distance;
import Data.Instance;
import DiversityControl.DistAdjustment;
import DiversityControl.OmegaAdjustment;
import DiversityControl.AcceptanceCriterion;
import DiversityControl.IdealDist;
import Improvement.LocalSearch;
import Improvement.IntraLocalSearch;
import Improvement.FeasibilityPhase;
import Perturbation.InsertionHeuristic;
import Perturbation.Perturbation;
import Solution.Solution;

public class AILSII
{
	//----------Problema------------
	Solution solution,referenceSolution,bestSolution;

	Instance instance;
	Distance pairwiseDistance;
	double bestF=Double.MAX_VALUE;
	double executionMaximumLimit;
	double optimal;

	//----------Warm Start------------
	String instanceFilePath;
	String warmStartPath;  // CLI-provided warm start path (empty = auto-detect)

	//----------Solution Output------------
	String solOutputPath;  // CLI-provided solution output path (empty = auto: solutions/<instance>.sol)
	long lastSaveTime;     // Track last hourly save time
	static final long SAVE_INTERVAL_MS = 3600000;  // 1 hour in milliseconds
	
	//----------caculoLimiar------------
	int numIterUpdate;

	//----------Metricas------------
	int iterator,iteratorMF;
	long first,ini;
	double timeAF,totalTime,time;
	
	Random rand=new Random();
	
	HashMap<String,OmegaAdjustment>omegaSetup=new HashMap<String,OmegaAdjustment>();

	double distanceLS;
	
	Perturbation[] pertubOperators;
	Perturbation selectedPerturbation;
	
	FeasibilityPhase feasibilityOperator;
	ConstructSolution constructSolution;
	
	LocalSearch localSearch;

	InsertionHeuristic insertionHeuristic;
	IntraLocalSearch intraLocalSearch;
	AcceptanceCriterion acceptanceCriterion;
//	----------Mare------------
	DistAdjustment distAdjustment;
//	---------Print----------
	boolean print=true;
	IdealDist idealDist;
	
	double epsilon;
	DecimalFormat deci=new DecimalFormat("0.0000");
	StoppingCriterionType stoppingCriterionType;
	
	public AILSII(Instance instance,InputParameters reader)
	{
		this.instance=instance;
		this.instanceFilePath=reader.getFile();
		this.warmStartPath=reader.getWarmStart();
		this.solOutputPath=reader.getSolOutput();
		Config config=reader.getConfig();
		this.optimal=reader.getBest();
		this.executionMaximumLimit=reader.getTimeLimit();
		
		this.epsilon=config.getEpsilon();
		this.stoppingCriterionType=config.getStoppingCriterionType();
		this.idealDist=new IdealDist();
		this.solution =new Solution(instance,config);
		this.referenceSolution =new Solution(instance,config);
		this.bestSolution =new Solution(instance,config);
		this.numIterUpdate=config.getGamma();
		
		this.pairwiseDistance=new Distance();
		
		this.pertubOperators=new Perturbation[config.getPerturbation().length];
		
		this.distAdjustment=new DistAdjustment( idealDist, config, executionMaximumLimit);
		
		this.intraLocalSearch=new IntraLocalSearch(instance,config);
		
		this.localSearch=new LocalSearch(instance,config,intraLocalSearch);
		
		this.feasibilityOperator=new FeasibilityPhase(instance,config,intraLocalSearch);
		
		this.constructSolution=new ConstructSolution(instance,config);
		
		OmegaAdjustment newOmegaAdjustment;
		for (int i = 0; i < config.getPerturbation().length; i++) 
		{
			newOmegaAdjustment=new OmegaAdjustment(config.getPerturbation()[i], config,instance.getSize(),idealDist);
			omegaSetup.put(config.getPerturbation()[i]+"", newOmegaAdjustment);
		}
		
		this.acceptanceCriterion=new AcceptanceCriterion(instance,config,executionMaximumLimit);

		try 
		{
			for (int i = 0; i < pertubOperators.length; i++) 
			{
				this.pertubOperators[i]=(Perturbation) Class.forName("Perturbation."+config.getPerturbation()[i]).
				getConstructor(Instance.class,Config.class,HashMap.class,IntraLocalSearch.class).
				newInstance(instance,config,omegaSetup,intraLocalSearch);
			}
			
		} catch (InstantiationException | IllegalAccessException | IllegalArgumentException
				| InvocationTargetException | NoSuchMethodException | SecurityException
				| ClassNotFoundException e) {
			e.printStackTrace();
		}
		
	}

	public void search()
	{
		iterator=0;
		first=System.currentTimeMillis();
		lastSaveTime=first;  // Initialize last save time
		referenceSolution.numRoutes=instance.getMinNumberRoutes();

		// Try warm start solution first
		boolean warmStartSuccess = tryWarmStart(referenceSolution);

		if(!warmStartSuccess)
		{
			System.out.println("================================================================================");
			System.out.println("[WARM START] FALLBACK: No warm start solution found. Using construction heuristic.");
			System.out.println("================================================================================");
			constructSolution.construct(referenceSolution);
		}

		feasibilityOperator.makeFeasible(referenceSolution);
		localSearch.localSearch(referenceSolution,true);
		bestSolution.clone(referenceSolution);
		while(!stoppingCriterion())
		{
			iterator++;

			solution.clone(referenceSolution);

			selectedPerturbation=pertubOperators[rand.nextInt(pertubOperators.length)];
			selectedPerturbation.applyPerturbation(solution);
			feasibilityOperator.makeFeasible(solution);
			localSearch.localSearch(solution,true);
			distanceLS=pairwiseDistance.pairwiseSolutionDistance(solution,referenceSolution);

			evaluateSolution();
			distAdjustment.distAdjustment();

			selectedPerturbation.getChosenOmega().setDistance(distanceLS);//update

			if(acceptanceCriterion.acceptSolution(solution))
				referenceSolution.clone(solution);

			// Check for hourly save
			checkAndSaveHourly();
		}

		totalTime=(double)(System.currentTimeMillis()-first)/1000;

		// Save final solution at termination
		saveBestSolution("FINAL");
	}

	/**
	 * Attempts to load a warm start solution.
	 * If a warm start path was provided via CLI (-warmStart), uses that path.
	 * Otherwise, auto-detects based on instance file path.
	 * Example: data/XL/XL-n1048-k237.vrp -> warm_start/XL/XL-n1048-k237.sol
	 *
	 * @param solution The solution object to populate
	 * @return true if warm start was successful, false otherwise
	 */
	private boolean tryWarmStart(Solution solution)
	{
		String resolvedPath;

		// Use CLI-provided path if available, otherwise auto-detect
		if(warmStartPath != null && !warmStartPath.isEmpty())
		{
			resolvedPath = warmStartPath;
			System.out.println("[WARM START] Using CLI-provided warm start path: " + resolvedPath);
		}
		else
		{
			resolvedPath = buildWarmStartPath(instanceFilePath);
			if(resolvedPath == null)
			{
				System.out.println("[WARM START] Could not determine warm start path from instance file: " + instanceFilePath);
				return false;
			}
		}

		File warmStartFile = new File(resolvedPath);
		if(!warmStartFile.exists())
		{
			System.out.println("[WARM START] Warm start file not found: " + resolvedPath);
			return false;
		}

		System.out.println("================================================================================");
		System.out.println("[WARM START] Loading warm start solution from: " + resolvedPath);

		boolean success = solution.loadWarmStartSolution(resolvedPath);

		if(success)
		{
			System.out.println("[WARM START] SUCCESS: Loaded warm start solution with " + solution.numRoutes + " routes, cost: " + solution.f);
			System.out.println("================================================================================");
		}
		else
		{
			System.out.println("[WARM START] FAILED: Could not parse warm start file: " + resolvedPath);
			System.out.println("================================================================================");
		}

		return success;
	}

	/**
	 * Builds the warm start file path based on the instance file path.
	 * Extracts the dataset name (parent folder) and instance name from the path.
	 * Example: data/XL/XL-n1048-k237.vrp -> warm_start/XL/XL-n1048-k237.sol
	 *
	 * @param instancePath The path to the .vrp instance file
	 * @return The path to the corresponding warm start .sol file, or null if path cannot be determined
	 */
	private String buildWarmStartPath(String instancePath)
	{
		if(instancePath == null || instancePath.isEmpty())
			return null;

		// Normalize path separators
		String normalizedPath = instancePath.replace("\\", "/");

		// Extract the filename without extension
		int lastSlash = normalizedPath.lastIndexOf('/');
		String filename;
		String parentFolder = "";

		if(lastSlash >= 0)
		{
			filename = normalizedPath.substring(lastSlash + 1);

			// Try to extract parent folder (dataset name)
			String parentPath = normalizedPath.substring(0, lastSlash);
			int secondLastSlash = parentPath.lastIndexOf('/');
			if(secondLastSlash >= 0)
			{
				parentFolder = parentPath.substring(secondLastSlash + 1);
			}
			else
			{
				parentFolder = parentPath;
			}
		}
		else
		{
			filename = normalizedPath;
		}

		// Remove .vrp extension if present
		if(filename.toLowerCase().endsWith(".vrp"))
		{
			filename = filename.substring(0, filename.length() - 4);
		}

		// Build warm start path: warm_start/<dataset>/<instance>.sol
		String warmStartPath;
		if(!parentFolder.isEmpty())
		{
			warmStartPath = "warm_start/" + parentFolder + "/" + filename + ".sol";
		}
		else
		{
			warmStartPath = "warm_start/" + filename + ".sol";
		}

		return warmStartPath;
	}

	/**
	 * Checks if an hour has passed since the last save and saves the best solution if so.
	 */
	private void checkAndSaveHourly()
	{
		long currentTime = System.currentTimeMillis();
		if(currentTime - lastSaveTime >= SAVE_INTERVAL_MS)
		{
			int hours = (int)((currentTime - first) / SAVE_INTERVAL_MS);
			saveBestSolution("HOUR_" + hours);
			lastSaveTime = currentTime;
		}
	}

	/**
	 * Saves the best solution to a file.
	 * @param tag A tag to identify this save (e.g., "HOUR_1", "FINAL")
	 */
	private void saveBestSolution(String tag)
	{
		String outputPath = buildSolOutputPath();
		if(outputPath == null)
		{
			System.out.println("[SOLUTION SAVE] ERROR: Could not determine output path");
			return;
		}

		// Create parent directories if they don't exist
		File outputFile = new File(outputPath);
		File parentDir = outputFile.getParentFile();
		if(parentDir != null && !parentDir.exists())
		{
			parentDir.mkdirs();
		}

		try
		{
			bestSolution.printSolution(outputPath);
			double elapsedTime = (double)(System.currentTimeMillis() - first) / 1000;
			System.out.println("[SOLUTION SAVE] " + tag + ": Saved best solution (cost: " + bestF +
				", K: " + bestSolution.numRoutes + ") to: " + outputPath + " at time: " + deci.format(elapsedTime) + "s");
		}
		catch(Exception e)
		{
			System.out.println("[SOLUTION SAVE] ERROR: Failed to save solution to: " + outputPath);
			e.printStackTrace();
		}
	}

	/**
	 * Builds the solution output file path.
	 * If solOutputPath was provided via CLI, uses that path.
	 * Otherwise, auto-generates path: solutions/<instance>.sol
	 *
	 * @return The path to save the solution file, or null if path cannot be determined
	 */
	private String buildSolOutputPath()
	{
		// Use CLI-provided path if available
		if(solOutputPath != null && !solOutputPath.isEmpty())
		{
			return solOutputPath;
		}

		// Auto-generate path: solutions/<instance>.sol
		if(instanceFilePath == null || instanceFilePath.isEmpty())
			return null;

		// Normalize path separators
		String normalizedPath = instanceFilePath.replace("\\", "/");

		// Extract the filename without extension
		int lastSlash = normalizedPath.lastIndexOf('/');
		String filename;

		if(lastSlash >= 0)
		{
			filename = normalizedPath.substring(lastSlash + 1);
		}
		else
		{
			filename = normalizedPath;
		}

		// Remove .vrp extension if present
		if(filename.toLowerCase().endsWith(".vrp"))
		{
			filename = filename.substring(0, filename.length() - 4);
		}

		// Build output path: solutions/<instance>.sol
		return "solutions/" + filename + ".sol";
	}

	public void evaluateSolution()
	{
		if((solution.f-bestF)<-epsilon)
		{		
			bestF=solution.f;
			
			bestSolution.clone(solution);
			iteratorMF=iterator;
			timeAF=(double)(System.currentTimeMillis()-first)/1000;
				
			if(print)
			{
				System.out.println("solution quality: "+bestF
				+" gap: "+deci.format(getGap())+"%"
				+" K: "+solution.numRoutes
				+" iteration: "+iterator
				+" eta: "+deci.format(acceptanceCriterion.getEta())
				+" omega: "+deci.format(selectedPerturbation.omega)
				+" time: "+timeAF
				);
			}
		}
	}
	
	private boolean stoppingCriterion()
	{
		switch(stoppingCriterionType)
		{
			case Iteration: 	if(bestF<=optimal||executionMaximumLimit<=iterator)
									return true;
								break;
							
			case Time: 	if(bestF<=optimal||executionMaximumLimit<(System.currentTimeMillis()-first)/1000)
							return true;
						break;
		}
		return false;
	}
	
	public static void main(String[] args) 
	{
		InputParameters reader=new InputParameters();
		reader.readingInput(args);
		
		Instance instance=new Instance(reader);
		
		AILSII ailsII=new AILSII(instance,reader);
		
		ailsII.search();
	}
	
	public Solution getBestSolution() {
		return bestSolution;
	}

	public double getBestF() {
		return bestF;
	}

	public double getGap()
	{
		return 100*((bestF-optimal)/optimal);
	}
	
	public boolean isPrint() {
		return print;
	}

	public void setPrint(boolean print) {
		this.print = print;
	}

	public Solution getSolution() {
		return solution;
	}

	public int getIterator() {
		return iterator;
	}

	public String printOmegas()
	{
		String str="";
		for (int i = 0; i < pertubOperators.length; i++) 
		{
			str+="\n"+omegaSetup.get(this.pertubOperators[i].perturbationType+""+referenceSolution.numRoutes);
		}
		return str;
	}
	
	public Perturbation[] getPertubOperators() {
		return pertubOperators;
	}
	
	public double getTotalTime() {
		return totalTime;
	}
	
	public double getTimePerIteration() 
	{
		return totalTime/iterator;
	}

	public double getTimeAF() {
		return timeAF;
	}

	public int getIteratorMF() {
		return iteratorMF;
	}
	
	public double getConvergenceIteration()
	{
		return (double)iteratorMF/iterator;
	}
	
	public double convergenceTime()
	{
		return (double)timeAF/totalTime;
	}
	
}
