import os
import sys
import unittest
#import platform
import numpy as np

try:
    import camb
except ImportError as e:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    import camb
#from camb import model, correlations, bbn, dark_energy, initialpower
#from camb.baseconfig import CAMBParamRangeError, CAMBValueError

fast = 'ci fast' in os.getenv("TRAVIS_COMMIT_MESSAGE", "")
 
class CambTest(unittest.TestCase):
 
    def testHMcode(self):

            # Parameters
            kmax_calc = 2e2 # Maximum wavenumber for the CAMB calculation [h/Mpc]
            pi = np.pi # Lovely pi
            twopi = 2.*pi # Twice as lovely pi
            As_def = 2e-9 # Default As value
            neutrino_number = 94.14 # Neutrino closure mass [eV] VERY LAZY
            eps_k = 1e-6 # Fractional error tolerated in k
            eps_a = 1e-6 # Fractional error tolerated in a
            eps_Pk = 5e-3 # Fractional error tolerated in Pk
            kmin_test = 1e-2 # Minimum wavenumber for test [h/Mpc]
            kmax_test = 1e1  # Maximum wavenumber for test [h/Mpc]
            amin_test = 0.333 # Minimum scale factor for test
            amax_test = 1.000 # Maximum scale factor for test
            Y_He = 0.24 # Helium fraction
            T_CMB = 2.725 # CMB temperature
            num_massive_nu = 3 # Number of massive neutrinos
            hierarchy = 'degenerate' # Neutrino hierarchy
            verbose = False # Verbose tests

            # Dictionary for HMcode versions
            HMcode_version_ihm = {
                'mead': 51,
                'mead2016': 51,
                'mead2015': 66,
                'mead2020': 123,
                'mead2020_feedback': 124
            }
            
            # Read in and sort Mead benchmark data
            def read_Mead_benchmark(infile):
                
                # Read data and split into k, a and Pk
                results = np.loadtxt(infile)
                k = results[:, 0]
                a = np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
                D2 = results[:, 1:]       
                Pk = (D2.T/(4.*pi*(k/twopi)**3)).T # Convert Delta^2(k) -> P(k)
                
                # Return results
                return k, a, Pk

            def HMcode_test_cosmologies(icos):

                # Common test parameters
                Om_m = 0.30
                Om_b = 0.05
                h = 0.7
                ns = 0.96
                sig8 = 0.8
                w0 = -1.
                wa = 0.
                mnu = 0.
                logT = 7.8
                
                # Uncommon test parameters
                if (icos == 56):
                    Om_m = 0.3158
                    Om_b = 0.04939
                    h = 0.6732
                    ns = 0.96605
                    sig8 = 0.8120
                    w0 = -1.
                    wa = 0.
                    mnu = 0.06
                elif (icos == 241):
                    w0 = -0.7
                elif (icos == 242):
                    w0 = -1.3
                elif (icos == 243):
                    mnu = 0.3
                elif (icos == 244):
                    mnu = 0.9
                elif (icos == 245):
                    ns = 0.7
                elif (icos == 246):
                    ns = 1.3
                elif (icos == 247):
                    Om_b = 0.01
                elif (icos == 248):
                    Om_b = 0.1
                elif (icos == 249):
                    wa = 0.9
                elif (icos == 250):
                    logT = 7.6
                elif (icos == 251):
                    logT = 8.0
                    
                # Return cosmological parameters
                return Om_m, Om_b, h, ns, sig8, w0, wa, mnu, logT

            # Set up a CAMB parameter set for a Mead cosmology
            def setup_HMcode_test(pars, icos):
                
                # Get the cosmological parameters for the cosmology
                Om_m, Om_b, h, ns, sig8, w0, wa, mnu, logT = HMcode_test_cosmologies(icos)

                # Derive and set CAMB parameters
                H0 = 100.*h
                wnu = mnu/neutrino_number
                Om_nu = wnu/h**2
                Om_c = Om_m-Om_b-Om_nu
                Om_k = 0.
                wb = Om_b*h**2
                wc = Om_c*h**2
                pars.set_cosmology(H0=H0, ombh2=wb, omch2=wc, mnu=mnu, omk=Om_k, YHe=Y_He, TCMB=T_CMB,
                    num_massive_neutrinos=num_massive_nu, neutrino_hierarchy=hierarchy)
                pars.set_dark_energy(w=w0, wa=wa, dark_energy_model='ppf')
                pars.InitPower.set_params(As=As_def, ns=ns)

                # Set parameters for matter spectrum calculation
                # It is wasteful to do this; could get As directly for each test cosmology
                pars.set_matter_power(redshifts=[0.], kmax=kmax_calc)
                pars.NonLinear = camb.model.NonLinear_none
                results = camb.get_results(pars)
                sig8_init = results.get_sigma8()
                As = As_def*(sig8/sig8_init)**2
                pars.InitPower.set_params(As=As, ns=ns) # Reset As

                # Return AGN temperature (ugly, but it needs to come out)
                return logT

            # Get the HMcode power from CAMB
            def get_HMcode_power_from_CAMB(pars, k_in, a_in, logT, HMcode_version):

                # k and z ranges for results
                kmin = k_in[0]
                kmax = k_in[-1]
                nk = len(k_in)
                z = -1.+1./a_in

                # Get non-linear spectra
                pars.set_matter_power(redshifts=z, kmax=kmax_calc)
                pars.NonLinear = camb.model.NonLinear_both
                results = camb.get_results(pars)
                results.calc_power_spectra(pars)
                results.Params.NonLinearModel.set_params(halofit_version=HMcode_version, HMCode_logT_AGN=logT)
                k, z, Pk = results.get_matter_power_spectrum(minkh=kmin, maxkh=kmax, npoints=nk)
                Pk = Pk.T[:, ::-1]
                z = np.array(z)[::-1]      
                a = 1./(1.+z)
                
                # Return non-linear power
                return k, a, Pk

            # Input file name
            def HMcode_benchmark_file(icos, ihm):
                return 'HMcode_test_outputs/HMcode_cos%d_hm%d.txt' % (icos, ihm)

            # Whitespace
            if(verbose): print('')

            # Loop over cosmologies
            #for icos in [26, 56, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251]:
            for icos in [26, 56]:

                # Loop over HMcode versions
                for HMcode_version in ['mead2015', 'mead2016', 'mead2020', 'mead2020_feedback']:    

                    # Read benchmark data
                    ihm = HMcode_version_ihm[HMcode_version]
                    infile = HMcode_benchmark_file(icos, ihm)
                    if(verbose): print('Infile:', infile)
                    k_in, a_in, Pk_in = read_Mead_benchmark(infile)

                    # Get power from CAMB
                    params = camb.CAMBparams(WantCls=False)
                    logT = setup_HMcode_test(params, icos)
                    k_nl, a_nl, Pk_nl = get_HMcode_power_from_CAMB(params, k_in, a_in, logT, HMcode_version)

                    # Compare benchmark to calculation
                    for ik in range(len(k_in)):
                        self.assertAlmostEqual(k_nl[ik]/k_in[ik], 1., delta=eps_k)
                    for ia in range(len(a_in)):
                        self.assertAlmostEqual(a_nl[ia]/a_in[ia], 1., delta=eps_a)
                    for ia in range(len(a_in)):
                        for ik in range(len(k_in)):
                            if (kmin_test <= k_in[ik] <= kmax_test and amin_test <= a_in[ia] <= amax_test):
                                self.assertAlmostEqual(Pk_nl[ik, ia]/Pk_in[ik, ia], 1., delta=eps_Pk)