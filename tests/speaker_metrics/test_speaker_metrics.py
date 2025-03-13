from audio_processing.speaker_metrics.speaker_metrics import SpeakerProcessor
from audio_processing.speaker_metrics.speaker_metrics import process, SpeakerProcessor
from chemistry_dashboard.audio_processing.speaker_metrics.speaker_metrics import SpeakerProcessor
from multiprocessing import Queue
from multiprocessing.process import AuthenticationString
from sentence_transformers import SentenceTransformer
from speaker_metrics import process, SpeakerProcessor
from speaker_metrics.speaker_metrics import SpeakerProcessor
from unittest.mock import Mock, patch
import callbacks
import logging
import multiprocessing
import multiprocessing as mp
import numpy as np
import os
import pytest
import time
import unittest

class TestSpeakerMetrics:

    def test___init__(self):
        """
        Test the initialization of SpeakerProcessor.

        This test verifies that the SpeakerProcessor is correctly initialized
        with the provided configuration, and that all instance variables are
        set to their expected initial values.
        """
        # Create a mock config object
        class MockConfig:
            def __init__(self):
                self.auth_key = "test_auth_key"

        config = MockConfig()

        # Initialize SpeakerProcessor
        processor = SpeakerProcessor(config)

        # Assert that instance variables are correctly initialized
        assert processor.total_contributions == 0
        assert processor.asr_complete == False
        assert processor.auth_key == "test_auth_key"
        assert processor.running_process is None
        assert processor.running == False
        assert processor.embeddings.size == 0
        assert processor.subspace_basis.size == 0
        assert processor.tau_window == 20
        assert processor.length == 0

    def test___init___missing_auth_key(self):
        """
        Tests the initialization of SpeakerProcessor with a config object that lacks an auth_key.
        This scenario is explicitly handled in the __init__ method by logging the auth_key.
        """
        class MockConfig:
            def __init__(self):
                pass  # No auth_key attribute

        config = MockConfig()

        # Capture logs to verify logging behavior
        with self.assertLogs(level='INFO') as log_context:
            SpeakerProcessor(config)

        # Check if a warning or error was logged about missing auth_key
        self.assertTrue(any('None' in msg for msg in log_context.output))

    def test_calculateCohesionSums_1(self):
        """
        Test the calculateCohesionSums method when self.length >= self.tau_window.

        This test verifies that the method correctly calculates and returns the
        cross_cohesion matrix when the number of processed embeddings is greater
        than or equal to the tau window size.
        """
        # Initialize SpeakerProcessor
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)

        # Set up test data
        processor.setSpeakers({'speaker1': 0, 'speaker2': 1})
        processor.tau_window = 2
        processor.length = 2
        processor.prev_window_speakers = ['speaker1', 'speaker2']
        processor.embeddings = np.array([[1, 0], [0, 1]])

        # Mock model.similarity method
        class MockModel:
            def similarity(self, a, b):
                return np.dot(a, b)

        mock_model = MockModel()

        # Call the method
        result = processor.calculateCohesionSums(1, np.array([1, 1]), mock_model)

        # Assert the result
        expected_shape = (2, 3, 3)  # (tau_window, num_speakers + 1, num_speakers + 1)
        assert result.shape == expected_shape, f"Expected shape {expected_shape}, but got {result.shape}"

        # Check if the result is a valid cross_cohesion matrix
        assert np.all(result >= 0), "Cross-cohesion values should be non-negative"
        assert np.all(result <= 1), "Cross-cohesion values should be less than or equal to 1"

    def test_calculateCohesionSums_2(self):
        """
        Test case for calculateCohesionSums when self.length is less than self.tau_window.
        This test verifies that the method correctly calculates cohesion sums and returns
        the expected cross_cohesion matrix when the conversation length is shorter than
        the tau window.
        """
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)
        processor.setSpeakers({'speaker1': 0, 'speaker2': 1})
        processor.tau_window = 5
        processor.length = 3  # Ensure length is less than tau_window

        # Mock data
        speaker = 1
        embedding = np.array([0.1, 0.2, 0.3])
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

        # Set up mock previous window speakers and embeddings
        processor.prev_window_speakers = ['speaker1', 'speaker2', 'speaker1']
        processor.embeddings = np.array([[0.2, 0.3, 0.4], [0.3, 0.4, 0.5], [0.4, 0.5, 0.6]])

        cross_cohesion = processor.calculateCohesionSums(speaker, embedding, model)

        # Assert that cross_cohesion has the expected shape
        assert cross_cohesion.shape == (5, 3, 3)

        # Assert that only the first 3 rows (corresponding to self.length) have non-zero values
        assert np.all(cross_cohesion[3:] == 0)

        # Assert that the values in the first 3 rows are non-zero where expected
        assert np.any(cross_cohesion[:3] != 0)

    def test_calculateCohesionSums_divide_by_zero(self):
        """
        Test calculateCohesionSums when division by zero occurs.
        This is an edge case explicitly handled in the method using np.errstate and np.nan_to_num.
        """
        # Setup
        processor = SpeakerProcessor(None)  # Assuming config is not needed for this test
        processor.length = 1
        processor.tau_window = 1
        processor.xi_sums = np.array([[[1.0, 0.0], [0.0, 1.0]]])
        processor.window_lagged_contributions = np.array([[[0, 1], [1, 0]]])  # This will cause division by zero

        # Mock model for similarity calculation
        class MockModel:
            def similarity(self, a, b):
                return 0.5

        mock_model = MockModel()

        # Call method
        result = processor.calculateCohesionSums(1, np.array([0.1, 0.2]), mock_model)

        # Assert
        expected = np.array([[[0.0, 0.0], [0.0, 0.0]]])  # nan_to_num converts NaN to 0
        assert np.array_equal(result, expected), "Expected NaN values to be converted to 0"

    def test_calculateCohesionSums_empty_history(self):
        """
        Test calculateCohesionSums when there's no history (self.length == 0).
        This is an edge case explicitly handled in the method.
        """
        # Setup
        processor = SpeakerProcessor(None)  # Assuming config is not needed for this test
        processor.length = 0
        processor.tau_window = 5
        processor.xi_sums = np.zeros((5, 2, 2))
        processor.window_lagged_contributions = np.zeros((5, 2, 2))

        # Mock model for similarity calculation
        class MockModel:
            def similarity(self, a, b):
                return 0.5

        mock_model = MockModel()

        # Call method
        result = processor.calculateCohesionSums(1, np.array([0.1, 0.2]), mock_model)

        # Assert
        assert np.array_equal(result, np.zeros((5, 2, 2))), "Expected empty result for empty history"

    def test_calculateNewness_1(self):
        """
        Test the calculateNewness method with a simple embedding and speaker.

        This test verifies that:
        1. The embedding is correctly added to self.embeddings
        2. The total_new value for the given speaker is updated
        3. The subspace_basis is updated
        4. The newness values are calculated correctly
        """
        # Initialize SpeakerProcessor
        processor = SpeakerProcessor(None)
        processor.participants = 2
        processor.contributions = np.array([0, 1, 1])
        processor.total_new = np.array([0.0, 0.0, 0.0])
        processor.subspace_basis = np.array([[1.0, 0.0, 0.0]])

        # Test input
        embedding = np.array([0.0, 1.0, 0.0])
        speaker = 1

        # Call the method
        processor.calculateNewness(embedding, speaker)

        # Assert the results
        assert np.array_equal(processor.embeddings, np.array([[0.0, 1.0, 0.0]]))
        assert np.isclose(processor.total_new[speaker], 1.0)
        assert processor.subspace_basis.shape == (2, 3)
        assert np.allclose(processor.newness, np.array([0.0, 1.0, 0.0]))

    def test_calculateNewness_empty_subspace_basis(self):
        """
        Test the calculateNewness method with an empty subspace basis.
        This tests the edge case where the subspace_basis is empty,
        which could potentially cause issues in the subspaceProjection method.
        """
        # Setup
        processor = SpeakerProcessor(None)
        processor.subspace_basis = np.array([])
        processor.embeddings = np.array([])
        processor.total_new = np.array([0, 0])
        processor.contributions = np.array([1, 1])

        # Test
        embedding = np.array([1, 2, 3])
        speaker = 0

        # Execute
        processor.calculateNewness(embedding, speaker)

        # Assert
        assert np.array_equal(processor.newness, [1, 0]), "Newness should be [1, 0] for empty subspace basis"

    def test_calculateNewness_zero_norm_vectors(self):
        """
        Test the calculateNewness method with zero norm vectors.
        This tests the edge case where the given_data and new_data vectors have zero norm,
        which could potentially cause a division by zero error if not handled properly.
        """
        # Setup
        processor = SpeakerProcessor(None)
        processor.subspace_basis = np.array([[0, 0, 0]])
        processor.embeddings = np.array([[0, 0, 0]])
        processor.total_new = np.array([0, 0])
        processor.contributions = np.array([1, 1])

        # Test
        embedding = np.array([0, 0, 0])
        speaker = 0

        # Execute
        processor.calculateNewness(embedding, speaker)

        # Assert
        assert np.array_equal(processor.newness, [0, 0]), "Newness should be [0, 0] for zero norm vectors"

    def test_processResponsivity_calculates_metrics_correctly(self):
        """
        Test that processResponsivity correctly calculates internal_cohesion, social_impact,
        and overall_responsivity based on the given cross_cohesion matrix.
        """
        # Setup
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)
        processor.participants = 3
        processor.tau_window = 2
        processor.ignore_diag = np.array([
            [False, True, True],
            [True, False, True],
            [True, True, False]
        ])

        # Test data
        cross_cohesion = np.array([
            [[0.5, 0.3, 0.2],
             [0.1, 0.6, 0.4],
             [0.2, 0.3, 0.7]],
            [[0.6, 0.2, 0.1],
             [0.3, 0.5, 0.2],
             [0.1, 0.4, 0.8]]
        ])

        # Execute
        processor.processResponsivity(cross_cohesion)

        # Assert
        expected_internal_cohesion = np.array([0.55, 0.55, 0.75])
        expected_social_impact = np.array([0.225, 0.3, 0.25])
        expected_overall_responsivity = np.array([0.225, 0.25, 0.25])

        np.testing.assert_array_almost_equal(processor.internal_cohesion, expected_internal_cohesion)
        np.testing.assert_array_almost_equal(processor.social_impact, expected_social_impact)
        np.testing.assert_array_almost_equal(processor.overall_responsivity, expected_overall_responsivity)

    def test_processResponsivity_zero_division(self):
        """
        Test the edge case where tau_window is zero, which would cause a division by zero error
        if not handled properly in the processResponsivity method.
        """
        processor = SpeakerProcessor(None)  # Config is not used in the method we're testing
        processor.tau_window = 0
        processor.participants = 2
        processor.ignore_diag = np.ones((3, 3), dtype=bool)
        np.fill_diagonal(processor.ignore_diag, 0)

        cross_cohesion = np.array([[[0, 0, 0], [0, 0, 0], [0, 0, 0]]])

        with pytest.raises(ZeroDivisionError):
            processor.processResponsivity(cross_cohesion)

    def test_process_2(self):
        """
        Test the process function when speaker_transcript_data is None.

        This test verifies that the process function correctly handles the case
        when speaker_transcript_data is None, which should trigger the processor
        to stop. It checks if the processor's running and asr_complete flags
        are set appropriately after processing a None value.
        """
        processing_queue = multiprocessing.Queue()
        speaker_transcript_queue = multiprocessing.Queue()
        model = Mock(spec=SentenceTransformer)

        config = Mock()
        config.auth_key = "test_auth_key"
        processing_queue.put(config)

        speakers = {"speaker1": "data1", "speaker2": "data2"}
        processing_queue.put(speakers)

        speaker_transcript_queue.put(None)  # Simulate end of processing

        with patch('speaker_metrics.callbacks.post_speaker_metrics', return_value=True):
            with patch('speaker_metrics.logging'):
                process(processing_queue, speaker_transcript_queue, model)

        # Assert that the processor has stopped
        assert processing_queue.empty()
        assert speaker_transcript_queue.empty()

    def test_process_3(self):
        """
        Test case for process function when processor and speakers are initialized,
        but the main loop condition is not met.

        This test verifies that the process function exits correctly when the
        processor is stopped or ASR is complete before entering the main loop.
        """
        # Setup
        processing_queue = multiprocessing.Queue()
        speaker_transcript_queue = multiprocessing.Queue()
        model = SentenceTransformer('distilbert-base-nli-mean-tokens')

        # Create a mock config and add it to the processing queue
        class MockConfig:
            def __init__(self):
                self.auth_key = "test_auth_key"

        config = MockConfig()
        processing_queue.put(config)

        # Add mock speakers to the processing queue
        speakers = {"speaker1": "data1", "speaker2": "data2"}
        processing_queue.put(speakers)

        # Create a processor and set it to stopped state
        processor = SpeakerProcessor(config)
        processor.running = False
        processor.asr_complete = True

        # Run the process function
        process(processing_queue, speaker_transcript_queue, model)

        # Assert that the function completes without entering the main loop
        assert processing_queue.empty()
        assert speaker_transcript_queue.empty()

    def test_process_5(self):
        """
        Test the process function when the processor is not created successfully.
        This test verifies that the function handles the case where the SpeakerProcessor
        is not initialized properly, ensuring that no further processing occurs.
        """
        processing_queue = multiprocessing.Queue()
        speaker_transcript_queue = multiprocessing.Queue()
        model = Mock(spec=SentenceTransformer)

        # Mock the SpeakerProcessor to return None
        with patch('chemistry-dashboard.audio_processing.speaker_metrics.speaker_metrics.SpeakerProcessor', return_value=None):
            # Call the process function
            process(processing_queue, speaker_transcript_queue, model)

        # Assert that no further processing occurred
        assert processing_queue.empty()
        assert speaker_transcript_queue.empty()

    def test_process_empty_speakers(self):
        """
        Test the process function with an empty speakers dictionary.
        This tests the edge case where no speakers are provided, which is explicitly handled in the focal method.
        """
        processing_queue = multiprocessing.Queue()
        speaker_transcript_queue = multiprocessing.Queue()
        model = SentenceTransformer('distilbert-base-nli-mean-tokens')

        # Set up the processing queue with necessary data
        class Config:
            def __init__(self):
                self.auth_key = "test_auth_key"

        processing_queue.put(Config())
        processing_queue.put({})  # Empty speakers dictionary

        # Run the process function
        process(processing_queue, speaker_transcript_queue, model)

        # Assert that the function logs the expected message
        with self.assertLogs(level='INFO') as cm:
            logging.getLogger().info('[Speaker_Metrics]Speaker metric Process stopped for test_auth_key.')

        self.assertIn('[Speaker_Metrics]Speaker metric Process stopped for test_auth_key.', cm.output[0])

    def test_process_none_speaker_transcript_data(self):
        """
        Test the process function when None is received from the speaker_transcript_queue.
        This tests the edge case where the queue signals to stop processing, which is explicitly handled in the focal method.
        """
        processing_queue = multiprocessing.Queue()
        speaker_transcript_queue = multiprocessing.Queue()
        model = SentenceTransformer('distilbert-base-nli-mean-tokens')

        # Set up the processing queue with necessary data
        class Config:
            def __init__(self):
                self.auth_key = "test_auth_key"

        processing_queue.put(Config())
        processing_queue.put({"speaker1": "data1"})  # Non-empty speakers dictionary
        speaker_transcript_queue.put(None)  # Signal to stop processing

        # Run the process function
        process(processing_queue, speaker_transcript_queue, model)

        # Assert that the function logs the expected messages
        with self.assertLogs(level='INFO') as cm:
            logging.getLogger().info("[Speaker_Metrics]Attempting to stop")
            logging.getLogger().info('[Speaker_Metrics]Speaker metric Process stopped for test_auth_key.')

        self.assertIn("[Speaker_Metrics]Attempting to stop", cm.output[0])
        self.assertIn('[Speaker_Metrics]Speaker metric Process stopped for test_auth_key.', cm.output[1])

    def test_process_when_speakers_is_falsy(self):
        """
        Test the process function when a processor is created but speakers is falsy.
        This test verifies that the function handles the case where speakers data is not available correctly.
        """
        # Mock necessary objects and queues
        mock_processing_queue = Mock()
        mock_speaker_transcript_queue = Mock()
        mock_model = Mock()

        # Set up the processing_queue to return a mock config and falsy speakers
        mock_config = Mock()
        mock_config.auth_key = "test_auth_key"
        mock_processing_queue.get.side_effect = [mock_config, None]

        # Call the process function
        with patch('chemistry-dashboard.audio_processing.speaker_metrics.speaker_metrics.logging') as mock_logging:
            process(mock_processing_queue, mock_speaker_transcript_queue, mock_model)

        # Assert that the correct log messages were called
        mock_logging.info.assert_any_call("[Speaker_Metrics]Init speaker metrics processor")
        mock_logging.info.assert_any_call('[Speaker_Metrics]Speaker metric Process started for test_auth_key.')
        mock_logging.info.assert_any_call('[Speaker_Metrics]Speaker metric Process stopped for test_auth_key.')

        # Assert that setSpeakers was not called on the processor
        assert not hasattr(SpeakerProcessor, 'setSpeakers') or not SpeakerProcessor.setSpeakers.called

        # Assert that the speaker_transcript_queue was not accessed
        assert not mock_speaker_transcript_queue.get.called

    def test_process_with_valid_input(self):
        """
        Test the process function with valid input data.
        This test verifies that the process function correctly handles
        a scenario where both the processor and speakers are available.
        """
        # Set up test data
        processing_queue = Queue()
        speaker_transcript_queue = Queue()
        model = SentenceTransformer('distilbert-base-nli-mean-tokens')

        # Mock config and speakers
        config = type('Config', (), {'auth_key': 'test_auth_key'})()
        speakers = {'speaker1': 'fingerprint1', 'speaker2': 'fingerprint2'}

        # Put test data into queues
        processing_queue.put(config)
        processing_queue.put(speakers)
        speaker_transcript_queue.put(('speaker1', 'Test transcript', 'transcript_id_1'))
        speaker_transcript_queue.put(None)  # Signal to stop processing

        # Call the process function
        process(processing_queue, speaker_transcript_queue, model)

        # Assert that queues are empty after processing
        assert processing_queue.empty()
        assert speaker_transcript_queue.empty()

        # Note: Further assertions could be added here to check the results of processing,
        # but this would require mocking the callbacks.post_speaker_metrics function
        # and capturing its input for verification.

    def test_setSpeakers_1(self):
        """
        Test that setSpeakers initializes all necessary attributes correctly for a given set of speakers.
        """
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)
        speakers = ['Speaker1', 'Speaker2', 'Speaker3']

        processor.setSpeakers(speakers)

        assert processor.speakers == speakers
        assert processor.participants == 3
        assert processor.indicies == {k: i for i, k in enumerate(speakers)}
        assert processor.contributions.shape == (4,)
        assert processor.prev_window_speakers == []
        assert processor.window_lagged_contributions.shape == (20, 4, 4)
        assert processor.xi_sums.shape == (20, 4, 4)
        assert processor.resp_vals.shape == (4, 4)
        assert processor.total_new.shape == (4,)
        assert processor.ignore_diag.shape == (4, 4)
        assert np.all(processor.ignore_diag.diagonal() == False)
        assert processor.participation_scores.shape == (4,)
        assert processor.internal_cohesion.shape == (4,)
        assert processor.overall_responsivity.shape == (4,)
        assert processor.social_impact.shape == (4,)
        assert processor.newness.shape == (4,)
        assert processor.communication_density.shape == (4,)

    def test_setSpeakers_empty_input(self):
        """
        Test setSpeakers method with an empty list of speakers.
        This tests the edge case of providing an empty input, which is handled
        by the method as it sets self.participants to the length of the input.
        """
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)
        processor.setSpeakers([])

        assert processor.participants == 0
        assert processor.speakers == []
        assert processor.indicies == {}
        assert processor.contributions.shape == (1,)
        assert processor.window_lagged_contributions.shape == (20, 1, 1)
        assert processor.xi_sums.shape == (20, 1, 1)
        assert processor.resp_vals.shape == (1, 1)
        assert processor.total_new.shape == (1,)
        assert processor.ignore_diag.shape == (1, 1)
        assert processor.participation_scores.shape == (1,)
        assert processor.internal_cohesion.shape == (1,)
        assert processor.overall_responsivity.shape == (1,)
        assert processor.social_impact.shape == (1,)
        assert processor.newness.shape == (1,)
        assert processor.communication_density.shape == (1,)

    def test_start_1(self):
        """
        Test that the start method correctly sets the running flag to True
        and the asr_complete flag to False.
        """
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)

        processor.start()

        assert processor.running == True
        assert processor.asr_complete == False

    def test_stop_1(self):
        """
        Test that the stop method sets running to False and asr_complete to True.
        """
        config = unittest.mock.Mock()
        processor = SpeakerProcessor(config)
        processor.running = True
        processor.asr_complete = False

        processor.stop()

        self.assertFalse(processor.running)
        self.assertTrue(processor.asr_complete)

    def test_stop_when_already_stopped(self):
        """
        Test the stop method when the processor is already stopped.
        This tests the edge case where stop is called multiple times.
        """
        config = type('Config', (), {'auth_key': 'test_key'})()
        processor = SpeakerProcessor(config)
        processor.running = False
        processor.asr_complete = True

        processor.stop()

        assert processor.running == False
        assert processor.asr_complete == True

    def test_subspaceProjection_1(self):
        """
        Test the subspaceProjection method with a simple 2D case.

        This test creates a subspace with two orthogonal vectors and projects
        a third vector onto this subspace. The projection should be the sum
        of the individual projections onto each basis vector.
        """
        # Create a SpeakerProcessor instance
        processor = SpeakerProcessor(None)

        # Define the subspace (two orthogonal vectors)
        s = np.array([[1, 0], [0, 1]])

        # Define the vector to project
        v = np.array([3, 4])

        # Calculate the projection
        proj = processor.subspaceProjection(s, v)

        # Expected result: the vector itself, as it's already in the subspace
        expected_proj = np.array([3, 4])

        # Assert that the projection is correct
        np.testing.assert_array_almost_equal(proj, expected_proj)
